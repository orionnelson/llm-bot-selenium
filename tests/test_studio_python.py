import ast
import unittest
from triage.studio_python import evaluate_branch, starter_source, export_workflow, validate_source, loop_values

class StudioPythonTests(unittest.TestCase):
    def node(self, **config):
        return {'id': 'branch', 'data': {'action': 'condition', 'label': 'i > 3', 'config': {'condition': {'input': 'i', 'operator': '>', 'threshold': 3, 'sample': 5}, **config}}}

    def test_numeric_branch_and_input_validation(self):
        c = self.node()['data']['config']['condition']
        self.assertEqual(evaluate_branch(c, {'i': 4}), {'branch': 'yes'})
        self.assertEqual(evaluate_branch(c, {'i': 3}), {'branch': 'no'})
        for value in (True, '4', float('nan'), float('inf')):
            with self.assertRaises(ValueError): evaluate_branch(c, {'i': value})
        with self.assertRaises(ValueError): evaluate_branch({**c, 'operator': '__import__'}, {'i': 4})
        with self.assertRaises(ValueError): evaluate_branch({**c, 'input': 'class'}, {'i': 4})

    def test_starter_python_is_syntactically_valid_and_uses_config(self):
        source = starter_source(self.node())
        validate_source(source)
        self.assertIn('i > 3', source)
        self.assertIn("inputs['i']", source)

    def test_edited_code_preserved_but_never_executed(self):
        marker = 'raise RuntimeError("MUST NOT EXECUTE")\ndef run(inputs, context=None):\n    return {"branch": "no"}\n'
        workflow = {'version': 1, 'nodes': [self.node(python={'source': marker, 'origin': 'user'})]}
        exported = export_workflow(workflow)
        ast.parse(exported)
        self.assertIn('MUST NOT EXECUTE', exported)
        self.assertIn('def node_0(', exported)
        self.assertIn('NOT safety', exported)

    def test_export_rejects_invalid_syntax_and_contract(self):
        for code in ('def run(', 'def other(inputs, context=None):\n    pass', 'def run(secret):\n    pass'):
            with self.assertRaises(ValueError): validate_source(code)
        with self.assertRaises(ValueError): export_workflow({'version': 99, 'nodes': []})

    def test_bounded_for_and_while_config(self):
        c = {'mode': 'for', 'variable': 'i', 'start': 0, 'stop': 3, 'step': 1, 'operator': '<', 'maxIterations': 5}
        self.assertEqual(loop_values(c), [0, 1, 2])
        self.assertEqual(loop_values({**c, 'mode': 'while'}), [0, 1, 2])
        self.assertEqual(loop_values({**c, 'start': 3, 'stop': 0, 'step': -1}), [3, 2, 1])
        with self.assertRaises(ValueError): loop_values({**c, 'mode': 'while', 'operator': '>=', 'stop': 0})

    def test_loop_python_export_reflects_loop_form(self):
        c = {'mode': 'for', 'variable': 'i', 'start': 0, 'stop': 3, 'step': 1, 'operator': '<', 'maxIterations': 5}
        node = {'id': 'loop', 'data': {'action': 'loop', 'config': {'loop': c}}}
        source = starter_source(node)
        validate_source(source)
        self.assertIn('for i in range(0, 3, 1)', source)
        c['mode'] = 'while'
        source = starter_source(node)
        validate_source(source)
        self.assertIn('while i < 3', source)
        self.assertIn('Loop iteration cap reached', source)

    def test_invalid_loop_bounds_fail_closed(self):
        c = {'mode': 'for', 'variable': 'i', 'start': 0, 'stop': 3, 'step': 1, 'operator': '<', 'maxIterations': 5}
        for patch in ({'step': 0}, {'step': True}, {'maxIterations': 101}, {'variable': 'i; import os'}):
            with self.assertRaises(ValueError): loop_values({**c, **patch})

    def test_pending_integrations_do_not_claim_execution(self):
        source = starter_source({'id':'lambda', 'data':{'action':'lambda','config':{'target':'user-function'}}})
        validate_source(source)
        self.assertIn('pending', source)
        self.assertIn('Execution adapter not connected', source)

if __name__ == '__main__':
    unittest.main()
