"""Export saved, reviewed synthetic DAG data and complete verified traces to one .py."""
import argparse
import hashlib
import json
from pathlib import Path

from .dag import DAG, load_python
from .standalone_runtime import ReplayFailure, identity, require, validate_spec, validate_step, approved_url

WAIT = {'kind': 'ready_region', 'timeout': 10}


def action(op, before, after, **fields):
    return dict(op=op, pre_url=before, post_url=after, wait=dict(WAIT), **fields)


def known_starter(task):
    """Recognize the existing Python and UI boilerplates, not arbitrary starter-labelled code."""
    from .studio_python import starter_source
    source = task.implementation.source
    if not source.strip():
        return True
    if task.implementation.origin != 'starter':
        return False
    python = starter_source({'data': {'action': task.action, 'config': task.params}})
    if task.action in ('start', 'end'):
        status = 'started' if task.action == 'start' else 'completed'
        ui = '# Editable Python starter.\ndef run(inputs, context=None):\n    return {"status": "' + status + '"}\n'
    else:
        payload = {'action': task.action, **{k: task.params[k] for k in ('target', 'region', 'metrics', 'timeRange', 'method', 'snippet') if k in task.params}}
        literal = json.dumps(json.dumps(payload, ensure_ascii=False, separators=(',', ':')), ensure_ascii=False)
        ui = ('# Editable Python starter. Integrations and webpage discovery are pending.\nimport json\n\n'
              'def run(inputs, context=None):\n    config = json.loads(' + literal + ')\n'
              '    return {"status": "pending", "action": config["action"],\n'
              '            "config": config, "reason": "Execution adapter not connected"}\n')
    return source in (python, ui)


def serial_tasks(dag):
    dag.validate()
    lookup = {t.task_id: t for t in dag.tasks}
    for t in dag.tasks:
        identity(t.task_id)
        require(t.kind in ('start', 'end', 'action') and t.scope is None and
                t.action not in ('parallel', 'snippet', 'condition', 'loop', 'loop-end'),
                'Unsupported branch/loop/parallel/snippet task; export requires a fully serial DAG')
        require(t.action in ('start', 'end', 'application'), 'Unsupported canonical action name')
        require(t.kind == t.action if t.action in ('start', 'end') else t.kind == 'action', 'Start/End must be structural')
        require(t.predicate is None and not t.params.get('snippet'), 'Unresolved predicate/snippet task cannot be exported')
        require(known_starter(t),
                'Custom-source task cannot be exported; review explicit semantic replay data separately')
        require(t.retries == 0 or t.kind in ('start', 'end'), 'Replay does not support canonical retries; save retries=0')
        if t.kind in ('start', 'end'):
            defaults = {'target': 'user-function', 'region': 'ca-central-1', 'metrics': ['Errors', 'Throttles', 'Duration'],
                        'timeRange': '1h', 'method': 'Auto', 'screenshot': True,
                        'prompt': 'Inspect {{ target }}. Summarize only observed operational evidence and identify uncertainty.'}
            parameters = {k: v for k, v in t.params.items() if k not in ('retries', 'timeout')}
            require(all(t.params[k] == getattr(t, k) for k in ('retries', 'timeout') if k in t.params) and
                    t.action == t.kind and (not parameters or parameters == defaults), 'Structural task contains action data')
    roots = [t for t in dag.tasks if not t.depends_on]
    require(len(roots) == 1 and roots[0].kind == 'start', 'Exactly one structural Start required; order cannot be guessed')
    result, seen, current = [], set(), roots[0]
    while True:
        require(current.task_id not in seen, 'Cyclic replay chain')
        seen.add(current.task_id)
        result.append(current)
        if current.kind == 'end':
            require(not current.routes, 'End has outgoing actions')
            break
        require(set(current.routes) == {'next'}, 'Explicit serial next dependency required')
        following = lookup[current.routes['next']]
        require(tuple(following.depends_on) == (current.task_id,), 'Parallel/ambiguous dependencies cannot be exported')
        current = following
    require(len(seen) == len(dag.tasks), 'Disconnected tasks cannot be omitted')
    require(len(result) > 2, 'DAG has no replay actions')
    return result[1:-1]


def recorded_steps(task, record, revision, urls):
    """Convert EVERY performed action; never derive replay from observation/model text."""
    approval = task.params.get('replay_capture')
    require(isinstance(approval, dict) and set(approval) == {'synthetic'} and approval['synthetic'] is True,
            'Task lacks approved synthetic replay metadata; approve and recapture')
    require(isinstance(record, dict) and record.get('version') == 'browser-run/v1' and
            record.get('status') == 'passed' and record.get('taskId') == task.task_id and
            record.get('revision') == revision and not record.get('journey'),
            'Completed run for this canonical revision required; legacy/public journeys need annotated recapture')
    policy = task.params.get('browser')
    require(isinstance(policy, dict) and set(policy) == {'allowed_actions', 'expected', 'max_steps'}
            and record.get('policy') == policy, 'Saved browser policy does not match recording; recapture')
    capture = record.get('replay')
    require(isinstance(capture, dict) and set(capture) == {'version', 'synthetic', 'context', 'initial', 'final'} and
            capture['version'] == 'sre-capture/v1' and capture['synthetic'] is True and capture['context'] == 'top-single-window',
            'Legacy run lacks approved URL/wait/boundary evidence; recapture with replay capture enabled')
    initial, final = capture['initial'], capture['final']
    require(initial == action('navigate', task.params.get('target'), task.params.get('target'), url=task.params.get('target')),
            'Initial navigation/wait evidence missing; recapture')
    rows = record.get('steps')
    require(isinstance(rows, list) and len(rows) <= policy['max_steps'], 'Incomplete or over-budget trace')
    result = [initial]
    for row in rows:
        require(row.get('action') == 'click' and row.get('state') == 'verified', 'Unverified or unsupported recorded action; recapture')
        s = row.get('replay')
        require(isinstance(s, dict) and s.get('op') == 'click' and s.get('id') in policy['allowed_actions'] and
                s.get('id') == row.get('candidate') and row.get('locator') == '[data-sre-action="' + s['id'] + '"]'
                and s.get('pre_url') == row.get('url') and s.get('post_url') == row.get('afterUrl'),
                'Missing/ambiguous recorded locator or action metadata; recapture')
        validate_step(s, urls)
        result.append(s)
    expected = policy['expected']
    require(final == action('assert_text', result[-1]['post_url'], result[-1]['post_url'], **expected)
            and record.get('verifiedResult') == expected['text'], 'Missing final visible assertion evidence; recapture')
    result.append(final)
    return result


def export_spec(dag, revision, urls, records=()):
    urls = sorted({approved_url(u) for u in urls})
    records = list(records)
    require(len(records) <= 100 and len({r.get('taskId') for r in records}) == len(records), 'Ambiguous duplicate browser runs')
    by_task = {r.get('taskId'): r for r in records}
    tasks, previous, used = [], None, set()
    for t in serial_tasks(dag):
        explicit = t.params.get('replay')
        if t.task_id in by_task:
            require(explicit is None, 'Choose explicit reviewed actions or recorded trace, not ambiguous evidence')
            steps = recorded_steps(t, by_task[t.task_id], revision, urls)
            used.add(t.task_id)
        else:
            require(isinstance(explicit, dict) and set(explicit) == {'version', 'synthetic', 'steps'} and
                    explicit['version'] == 'sre-replay-task/v1' and explicit['synthetic'] is True,
                    'Task ' + t.task_id + ' needs reviewed synthetic replay data or a complete current run; prompt-only tasks cannot export')
            steps = explicit['steps']
        tasks.append({'id': t.task_id, 'depends_on': [previous] if previous else [], 'timeout': min(t.timeout, 300), 'steps': steps})
        previous = t.task_id
    require(used == set(by_task), 'Run is not a task of the saved serial DAG')
    spec = {'version': 'sre-selenium/v1', 'revision': revision, 'urls': urls, 'tasks': tasks, 'run_timeout': 300}
    validate_spec(spec)
    spec['urls'] = sorted({s[k] for t in tasks for s in t['steps'] for k in ('pre_url', 'post_url', 'url', 'href') if s.get(k) is not None})
    return json.loads(json.dumps(spec, allow_nan=False))


def export_python(dag, revision, urls, records=()):
    spec = export_spec(dag, revision, urls, records)
    template = Path(__file__).with_name('standalone_runtime.py').read_text(encoding='utf-8')
    marker = 'SPEC = None  # Replaced with embedded JSON by the exporter, never executable task source.'
    require(template.count(marker) == 1, 'Standalone runtime template invalid')
    return template.replace(marker, 'SPEC = json.loads(' + repr(json.dumps(spec, ensure_ascii=True, allow_nan=False)) + ')')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('dag', type=Path)
    p.add_argument('--revision', required=True, help='Expected SHA256 of saved DAG bytes')
    p.add_argument('--urls', type=Path, required=True, help='Operator-approved synthetic URL JSON list')
    p.add_argument('--run', type=Path, action='append', default=[], help='Completed manifest (one per canonical task)')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    try:
        for path in [args.dag, args.urls, *args.run]:
            require(path.stat().st_size <= 1_000_000, 'Input exceeds 1 MB')
        raw = args.dag.read_bytes()
        revision = hashlib.sha256(raw).hexdigest()
        require(args.revision == revision, 'Stale canonical revision; reload before export')
        dag = load_python(raw.decode()) if args.dag.suffix == '.py' else DAG.from_spec(json.loads(raw))
        source = export_python(dag, revision, json.loads(args.urls.read_text()), [json.loads(r.read_text()) for r in args.run])
        require(hashlib.sha256(args.dag.read_bytes()).hexdigest() == revision, 'DAG changed during export')
        # Exclusive create: reviewed regeneration is a new artifact, never in-place repair.
        with args.output.open('x', encoding='utf-8') as out:
            out.write(source)
        print('Standalone artifact written; browser not executed')
    except (ValueError, TypeError, KeyError, OSError, SyntaxError, RecursionError, AttributeError) as error:
        p.exit(2, 'Export rejected: ' + (str(error) if type(error) is ReplayFailure else 'invalid or unavailable input/output') + '\n')


if __name__ == '__main__':
    main()
