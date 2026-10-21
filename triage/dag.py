"""Itemized functional DAGs using stdlib dataclasses + graphlib. Never executes handlers."""
from __future__ import annotations
import argparse
import ast
from dataclasses import asdict, dataclass, field
from graphlib import CycleError, TopologicalSorter
import json
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class PythonSource:
    source: str
    origin: str = 'user'
    review: str = 'pending'
    model: str | None = None

@dataclass(frozen=True)
class LoopSpec:
    mode: str
    variable: str
    start: int
    stop: int
    step: int
    operator: str
    max_iterations: int
    entry_id: str
    continue_id: str
    body_ids: tuple[str, ...]

@dataclass(frozen=True)
class Task:
    task_id: str
    label: str
    action: str
    kind: str = 'action'
    scope: str | None = None
    depends_on: tuple[str, ...] = ()
    routes: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    predicate: dict[str, Any] | None = None
    loop: LoopSpec | None = None
    implementation: PythonSource = field(default_factory=lambda: PythonSource(''))
    retries: int = 0
    timeout: int = 30

@dataclass(frozen=True)
class DAG:
    name: str
    tasks: tuple[Task, ...]

    def validate(self):
        from .studio_python import condition_config, numeric, starter_source
        if not isinstance(self.name, str) or len(self.name) > 160 or not isinstance(self.tasks, (tuple, list)) or not 1 <= len(self.tasks) <= 300 or any(not isinstance(t, Task) for t in self.tasks):
            raise ValueError('DAG requires a name and 1..300 itemized tasks')
        ids = [t.task_id for t in self.tasks]
        if any(not isinstance(i, str) or not i or len(i) > 150 for i in ids) or len(ids) != len(set(ids)):
            raise ValueError('Invalid or duplicate task IDs')
        lookup = {t.task_id: t for t in self.tasks}
        scopes = {None}
        for t in self.tasks:
            if t.kind not in {'action', 'start', 'end', 'branch', 'loop', 'continue', 'snippet'} or not isinstance(t.action, str) or len(t.action) > 100 or not isinstance(t.label, str) or len(t.label) > 160:
                raise ValueError('Invalid task identity or kind')
            if not isinstance(t.params, dict) or not isinstance(t.routes, dict) or isinstance(t.retries, bool) or not isinstance(t.retries, int) or not 0 <= t.retries <= 10 or isinstance(t.timeout, bool) or not isinstance(t.timeout, (int, float)) or not 1 <= t.timeout <= 3600:
                raise ValueError('Invalid task parameters or error policy')
            json.dumps(t.params, allow_nan=False)
            if not isinstance(t.implementation, PythonSource) or not isinstance(t.implementation.source, str) or len(t.implementation.source) > 30000 or t.implementation.origin not in {'starter', 'user', 'llm'} or t.implementation.review not in {'pending', 'approved'}:
                raise ValueError('Invalid inert Python implementation')
            if t.scope is not None:
                if t.scope not in lookup or lookup[t.scope].kind != 'loop' or t.scope == t.task_id:
                    raise ValueError('Task scope must name a parent loop')
                scopes.add(t.scope)
            if not isinstance(t.depends_on, (tuple, list)) or any(not isinstance(p, str) for p in t.depends_on) or len(t.depends_on) != len(set(t.depends_on)) or any(p not in lookup or lookup[p].scope != t.scope or p == t.task_id for p in t.depends_on):
                raise ValueError('Invalid dependency or dependency crosses loop scope')
            ports = {'branch': {'yes', 'no'}, 'loop': {'body', 'done'}, 'continue': set(), 'end': set()}.get(t.kind, {'next'})
            if any(not isinstance(k, str) or not isinstance(v, str) for k, v in t.routes.items()) or not set(t.routes) <= ports or any(target not in lookup for target in t.routes.values()):
                raise ValueError('Invalid route/port')
            if t.kind == 'branch':
                if set(t.routes) != {'yes', 'no'} or not t.predicate:
                    raise ValueError('Branch requires explicit IF / ELSE routes and predicate')
                condition_config(t.predicate)
                numeric(t.predicate.get('sample'))
                if t.predicate.get('source', 'input') not in {'input', 'lambda-errors'}: raise ValueError('Invalid predicate input binding')
            if t.kind == 'loop':
                if not isinstance(t.loop, LoopSpec):
                    raise ValueError('Loop task requires a LoopSpec')
                c = t.loop
                starter_source({'data': {'action': 'loop', 'config': {'loop': {'mode': c.mode, 'variable': c.variable, 'start': c.start, 'stop': c.stop, 'step': c.step, 'operator': c.operator, 'maxIterations': c.max_iterations}}}})
                actual = {x.task_id for x in self.tasks if x.scope == t.task_id}
                if set(c.body_ids) != actual or len(c.body_ids) != len(actual) or c.entry_id not in actual or c.continue_id not in actual or lookup[c.continue_id].kind != 'continue' or t.routes.get('body') != c.entry_id:
                    raise ValueError('Invalid loop body/entry/Continue references')
                # Every selected path inside this scope must terminate at its own Continue.
                seen = set()
                def body_path(task_id):
                    if task_id in seen: return
                    seen.add(task_id)
                    if task_id == c.continue_id: return
                    item = lookup[task_id]
                    next_ids = [v for k, v in item.routes.items() if not (item.kind == 'loop' and k == 'body')]
                    if not next_ids: raise ValueError('Loop body does not reach its Continue')
                    for target in next_ids:
                        if target not in actual: raise ValueError('Loop body escapes its scope')
                        body_path(target)
                body_path(c.entry_id)
            elif t.loop is not None:
                raise ValueError('Only a loop task may declare a LoopSpec')
            if t.kind == 'continue' and (t.scope is None or not isinstance(lookup[t.scope].loop, LoopSpec) or lookup[t.scope].loop.continue_id != t.task_id):
                raise ValueError('Orphan Continue boundary')
            for port, target in t.routes.items():
                if t.kind == 'loop' and port == 'body': continue
                if lookup[target].scope != t.scope:
                    raise ValueError('Route crosses a loop scope')
        # Scope hierarchy and every compound subgraph must be acyclic.
        try:
            tuple(TopologicalSorter({t.task_id: (t.scope,) if t.scope else () for t in self.tasks if t.kind == 'loop'}).static_order())
            for scope in scopes:
                self.topological_order(scope)
        except CycleError as exc:
            raise ValueError('DAG contains a dependency/scope cycle') from exc
        for t in self.tasks:
            incoming = {other.task_id for other in self.tasks if other.scope == t.scope and any(target == t.task_id for target in other.routes.values())}
            if incoming != set(t.depends_on):
                raise ValueError('Declared dependencies do not match task routes')
        return self

    def topological_order(self, scope=None):
        """Static order within root or a loop body. This does not run a task."""
        return tuple(TopologicalSorter({t.task_id: tuple(t.depends_on) for t in self.tasks if t.scope == scope}).static_order())

    def plan(self):
        self.validate()
        return {'root': self.topological_order(), 'bodies': {t.task_id: self.topological_order(t.task_id) for t in self.tasks if t.kind == 'loop'}, 'execution': 'not started'}

    def to_spec(self):
        data = json.loads(json.dumps({'version': 'sre-dag/v1', 'name': self.name, 'tasks': [asdict(t) for t in self.tasks]}, allow_nan=False))
        for t in data['tasks']:
            if t['implementation']['model'] is None: t['implementation'].pop('model')
        return data

    @classmethod
    def from_spec(cls, value):
        if not isinstance(value, dict) or value.get('version') != 'sre-dag/v1' or set(value) != {'version', 'name', 'tasks'} or not isinstance(value['tasks'], list) or len(value['tasks']) > 300:
            raise ValueError('Expected sre-dag/v1 definition')
        tasks = []
        for raw in value['tasks']:
            data = dict(raw)
            data['implementation'] = PythonSource(**data['implementation'])
            data['depends_on'] = tuple(data['depends_on'])
            if data.get('loop'):
                data['loop'] = LoopSpec(**{**data['loop'], 'body_ids': tuple(data['loop']['body_ids'])})
            tasks.append(Task(**data))
        return cls(name=value['name'], tasks=tuple(tasks)).validate()

    def to_python(self):
        """Constructors only; user/model implementation remains a quoted string."""
        def literal(value):
            if isinstance(value, (PythonSource, LoopSpec, Task)):
                fields = {name: getattr(value, name) for name in value.__dataclass_fields__}
                return type(value).__name__ + '(' + ', '.join(f'{k}={literal(v)}' for k, v in fields.items()) + ')'
            if isinstance(value, tuple): return '(' + ', '.join(literal(v) for v in value) + (',' if value else '') + ')'
            if isinstance(value, dict): return '{' + ', '.join(f'{k!r}: {literal(v)}' for k, v in value.items()) + '}'
            if isinstance(value, list): return '[' + ', '.join(literal(v) for v in value) + ']'
            return repr(value)
        self.validate()
        return '# Functional DAG; layout is separate. Handlers are inert strings, never executed here.\nfrom triage.dag import DAG, Task, LoopSpec, PythonSource\n\ndag = DAG(name=' + repr(self.name) + ', tasks=(\n' + ',\n'.join('    ' + literal(t) for t in self.tasks) + ',\n))\ndag.validate()\n'


def load_python(source):
    """Safe literal/constructor decoder; does not exec, eval or import submitted code."""
    if not isinstance(source, str) or len(source) > 1000000:
        raise ValueError('DAG Python exceeds 1 MB')
    tree = ast.parse(source)
    constructors = {'DAG': DAG, 'Task': Task, 'LoopSpec': LoopSpec, 'PythonSource': PythonSource}
    def decode(node, depth=0):
        if depth > 32: raise ValueError('DAG literal is too deeply nested')
        if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bool, type(None))): return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)) and isinstance(node.operand, ast.Constant) and type(node.operand.value) in (int, float): return -node.operand.value if isinstance(node.op, ast.USub) else node.operand.value
        if isinstance(node, (ast.Tuple, ast.List)):
            values = [decode(v, depth+1) for v in node.elts]
            return tuple(values) if isinstance(node, ast.Tuple) else values
        if isinstance(node, ast.Dict):
            keys = [decode(k, depth+1) for k in node.keys]
            if any(not isinstance(k, str) for k in keys) or len(keys) != len(set(keys)): raise ValueError('Invalid/duplicate dictionary keys')
            return dict(zip(keys, [decode(v, depth+1) for v in node.values]))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in constructors and not node.args and all(k.arg for k in node.keywords):
            if len({k.arg for k in node.keywords}) != len(node.keywords):
                raise ValueError('Duplicate constructor keyword in DAG definition')
            return constructors[node.func.id](**{k.arg: decode(k.value, depth+1) for k in node.keywords})
        raise ValueError('Only literal values and DAG/Task/LoopSpec/PythonSource constructors are accepted')
    dag = None
    for item in tree.body:
        if isinstance(item, ast.ImportFrom) and item.module == 'triage.dag' and not item.level and all(x.name in constructors and not x.asname for x in item.names): continue
        if isinstance(item, ast.Assign) and len(item.targets) == 1 and isinstance(item.targets[0], ast.Name) and item.targets[0].id == 'dag' and dag is None:
            dag = decode(item.value); continue
        if isinstance(item, ast.Expr) and isinstance(item.value, ast.Call):
            call = item.value
            if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.value.id == 'dag' and call.func.attr == 'validate' and not call.args and not call.keywords: continue
        raise ValueError('Unexpected executable statement in DAG definition')
    if not isinstance(dag, DAG): raise ValueError('Missing dag = DAG(...) definition')
    return dag.validate()


def from_workflow(workflow):
    """Legacy visual JSON adapter: layout is discarded, functional items are retained."""
    from .studio_python import starter_source
    if not isinstance(workflow, dict) or workflow.get('version') != 1 or not isinstance(workflow.get('nodes'), list) or not 1 <= len(workflow['nodes']) <= 300 or not isinstance(workflow.get('edges'), list) or len(workflow['edges']) > 1000:
        raise ValueError('Invalid visual workflow')
    nodes = {n['id']: n for n in workflow['nodes']}
    if len(nodes) != len(workflow['nodes']): raise ValueError('Duplicate nodes')
    edges = workflow['edges']
    if any(e['source'] not in nodes or e['target'] not in nodes for e in edges): raise ValueError('Dangling edge')
    owners = {}
    def out(node_id): return [e for e in edges if e['source'] == node_id]
    for node_id, n in nodes.items():
        if n['data']['action'] != 'loop': continue
        c = n['data']['config']['loop']; entry = [e['target'] for e in out(node_id) if e.get('sourceHandle') == 'body']
        if len(entry) != 1: raise ValueError('Loop requires one BODY entry')
        seen = set()
        def visit(current):
            if current in seen: return
            if current == node_id: raise ValueError('Invalid body cycle')
            seen.add(current)
            if current == c['endNodeId']: return
            action = nodes[current]['data']['action']
            if action == 'loop-end': raise ValueError('Wrong Continue boundary')
            targets = [e['target'] for e in out(current) if action != 'loop' or e.get('sourceHandle') == 'done']
            if not targets: raise ValueError('Body does not reach Continue')
            for target in targets: visit(target)
        visit(entry[0])
        if c['endNodeId'] not in seen: raise ValueError('Missing Continue boundary')
        for member in seen:
            if member in owners: raise ValueError('Overlapping loop scopes')
            owners[member] = node_id
    tasks = []
    for node_id, n in nodes.items():
        data = n['data']; c = data['config']; action = data['action']; scope = owners.get(node_id)
        kind = 'branch' if action == 'condition' else 'continue' if action == 'loop-end' else action if action in {'loop','start','end','snippet'} else 'action'
        routes = {}
        for e in out(node_id):
            if action == 'loop-end':
                if e['target'] != c.get('loopOwner') or e.get('sourceHandle') != 'continue' or e.get('targetHandle') != 'repeat': raise ValueError('Invalid loop return')
                continue
            port = e.get('sourceHandle') or 'next'
            if port in routes: raise ValueError('Duplicate output port')
            routes[port] = e['target']
        deps = tuple(dict.fromkeys(e['source'] for e in edges if e['target'] == node_id and e.get('targetHandle') != 'repeat' and owners.get(e['source']) == scope))
        predicate = c.get('condition', {'input':'errors','operator':'>','threshold':0,'sample':5,'source':'lambda-errors'}) if kind == 'branch' else None
        loop = None
        if kind == 'loop':
            raw = c['loop']; loop = LoopSpec(raw['mode'],raw['variable'],raw['start'],raw['stop'],raw['step'],raw['operator'],raw['maxIterations'],routes['body'],raw['endNodeId'],tuple(i for i in nodes if owners.get(i) == node_id))
        params = {} if kind in {'branch','loop','continue'} else {k:v for k,v in c.items() if k not in {'python','loop','loopOwner','condition'}}
        implementation = PythonSource(**c['python']) if c.get('python') else PythonSource(starter_source(n),'starter','pending')
        tasks.append(Task(node_id,data['label'],action,kind,scope,deps,routes,params,predicate,loop,implementation,c['retries'],c['timeout']))
    return DAG(workflow['name'],tuple(tasks)).validate()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--format',choices=['python','spec','plan'],default='python')
    parser.add_argument('--layout',type=Path,help='Write a separate visual-layout JSON when compiling legacy visual JSON')
    args=parser.parse_args()
    if args.input.stat().st_size>1000000: parser.error('Input exceeds 1 MB')
    try:
        text=args.input.read_text(); value=None
        if args.input.suffix=='.py': dag=load_python(text)
        else:
            value=json.loads(text);dag=DAG.from_spec(value) if value.get('version')=='sre-dag/v1' else from_workflow(value)
        output=dag.to_python() if args.format=='python' else json.dumps(dag.to_spec() if args.format=='spec' else dag.plan(),indent=2)
        if args.layout:
            if not value or value.get('version')!=1: raise ValueError('Separate layout requires original visual JSON')
            args.layout.write_text(json.dumps({'version':'sre-layout/v1','positions':{n['id']:n['position'] for n in value['nodes']}},indent=2))
        if args.output: args.output.write_text(output)
        else: print(output)
    except (ValueError,TypeError,KeyError,SyntaxError,CycleError) as exc: parser.error(str(exc))

if __name__=='__main__': main()
