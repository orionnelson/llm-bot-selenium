import json
from pathlib import Path
import tempfile
import unittest
from dataclasses import replace
from triage.dag import DAG, Task, LoopSpec, PythonSource, load_python, from_workflow

class DAGTests(unittest.TestCase):
    def simple(self):
        return DAG('Example', (Task('a','Start','start',kind='start',routes={'next':'b'}),Task('b','End','end',kind='end',depends_on=('a',))))

    def test_existing_graphlib_orders_real_dataclass_items(self):
        d=self.simple().validate()
        self.assertEqual(d.topological_order(),('a','b'))
        self.assertEqual(d.plan()['execution'],'not started')
        self.assertEqual(DAG.from_spec(d.to_spec()),d)

    def test_python_definition_roundtrip_preserves_inert_user_source(self):
        d=self.simple()
        with tempfile.TemporaryDirectory() as temp:
            marker=Path(temp)/'must-not-exist'
            source=f'from pathlib import Path\nPath({str(marker)!r}).write_text("UNSAFE")\ndef run(inputs, context=None):\n    return {{}}'
            d=replace(d,tasks=(replace(d.tasks[0],implementation=PythonSource(source,'user','pending')),d.tasks[1]))
            text=d.to_python()
            loaded=load_python(text)
            self.assertEqual(loaded.tasks[0].implementation.source,source)
            self.assertFalse(marker.exists())
            self.assertNotIn('position',loaded.to_spec())

    def test_dependency_cycle_and_missing_tasks_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'cycle'):
            DAG('Cycle',(Task('a','A','action',depends_on=('b',),routes={'next':'b'}),Task('b','B','action',depends_on=('a',),routes={'next':'a'}))).validate()
        with self.assertRaises(ValueError): replace(self.simple(),tasks=(replace(self.simple().tasks[0],depends_on=('missing',)),)).validate()

    def test_duplicate_ids_mismatched_dependencies_and_invalid_items_fail(self):
        d=self.simple()
        for tasks in ((d.tasks[0],d.tasks[0]),(d.tasks[0],replace(d.tasks[1],depends_on=())),(42,)):
            with self.assertRaises(ValueError): DAG('Invalid',tasks).validate()

    def test_executable_python_statements_and_unknown_constructors_are_never_accepted(self):
        valid=self.simple().to_python()
        for prefix in ('import os\n','open("/tmp/not-written", "w")\n','raise RuntimeError("not executed")\n'):
            with self.assertRaises(ValueError): load_python(prefix+valid)
        with self.assertRaises(ValueError): load_python('dag = __import__("os")')
        with self.assertRaises(ValueError): load_python('dag = DAG(name="x", tasks=tuple())')
        with self.assertRaises(ValueError): load_python('from evil import DAG\ndag = DAG(name="x", tasks=())')

    def test_python_literals_do_not_allow_expansions_attributes_or_comprehensions(self):
        for text in ('dag = DAG(**{})','dag = DAG(name="x", tasks=[x for x in []])','dag = DAG(name="x", tasks=().__class__)'):
            with self.assertRaises(ValueError): load_python(text)

    def test_duplicate_constructor_keywords_never_silently_replace_reviewed_values(self):
        source = self.simple().to_python()
        # ast.parse accepts duplicate keyword arguments even though Python compile rejects them.
        for original, duplicate in (
            ("DAG(name='Example'", "DAG(name='Hidden', name='Example'"),
            ("Task(task_id='a'", "Task(task_id='hidden', task_id='a'"),
            ("PythonSource(source=''", "PythonSource(source='hidden', source=''"),
        ):
            with self.subTest(constructor=original):
                self.assertIn(original, source)
                with self.assertRaisesRegex(ValueError, 'Duplicate constructor keyword'):
                    load_python(source.replace(original, duplicate, 1))
        spec = LoopSpec('for', 'i', 0, 3, 1, '<', 10, 'body', 'continue', ('body', 'continue'))
        loop = DAG('Loop', (
            Task('loop', 'For', 'loop', kind='loop', routes={'body': 'body', 'done': 'end'}, loop=spec),
            Task('body', 'Read', 'application', scope='loop', routes={'next': 'continue'}),
            Task('continue', 'Continue', 'loop-end', kind='continue', scope='loop', depends_on=('body',)),
            Task('end', 'End', 'end', kind='end', depends_on=('loop',)),
        )).to_python()
        with self.assertRaisesRegex(ValueError, 'Duplicate constructor keyword'):
            load_python(loop.replace("LoopSpec(mode='for'", "LoopSpec(mode='while', mode='for'", 1))

    def test_cli_does_not_publish_transport_for_ambiguous_python(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ambiguous.py'
            output = Path(directory) / 'definition.json'
            path.write_text(self.simple().to_python().replace("DAG(name='Example'", "DAG(name='Hidden', name='Example'", 1))
            result = subprocess.run([sys.executable, '-m', 'triage.dag', str(path), '--format', 'spec', '--output', str(output)], capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Duplicate constructor keyword', result.stderr)
            self.assertFalse(output.exists())

    def test_loop_is_a_compound_body_scope_not_a_cyclic_dependency(self):
        c=LoopSpec('for','i',0,3,1,'<',10,'body','continue',('body','continue'))
        d=DAG('Loop',(Task('loop','For','loop',kind='loop',routes={'body':'body','done':'end'},loop=c),Task('body','Read','application',scope='loop',routes={'next':'continue'}),Task('continue','Continue','loop-end',kind='continue',scope='loop',depends_on=('body',)),Task('end','End','end',kind='end',depends_on=('loop',))))
        self.assertEqual(d.plan()['root'],('loop','end'))
        self.assertEqual(d.plan()['bodies']['loop'],('body','continue'))
        self.assertEqual(load_python(d.to_python()),d)
        with self.assertRaises(ValueError): replace(d,tasks=(replace(d.tasks[0],loop=replace(c,max_iterations=101)),)+d.tasks[1:]).validate()

    def test_scopes_and_orphan_continue_are_rejected(self):
        with self.assertRaises(ValueError): DAG('No owner',(Task('c','Continue','loop-end',kind='continue'),)).validate()
        with self.assertRaises(ValueError): DAG('Missing scope',(Task('x','X','action',scope='missing'),)).validate()

    def test_visual_layout_adapter_separates_positions_from_function(self):
        cfg={'target':'example','region':'ca-central-1','metrics':[],'timeRange':'1h','method':'Auto','screenshot':False,'prompt':'Read only','retries':0,'timeout':30}
        w={'version':1,'name':'Adapter','nodes':[{'id':'a','position':{'x':10,'y':20},'data':{'action':'start','label':'Start','config':cfg}},{'id':'b','position':{'x':200,'y':20},'data':{'action':'end','label':'End','config':cfg}}],'edges':[{'source':'a','target':'b'}]}
        d=from_workflow(w)
        self.assertEqual(d.topological_order(),('a','b'))
        self.assertNotIn('position',json.dumps(d.to_spec()))
        self.assertIn('Task(',d.to_python())
        w['nodes'][0]['position']={'x':900,'y':300}
        self.assertEqual(from_workflow(w).to_spec(),d.to_spec())

if __name__=='__main__': unittest.main()
