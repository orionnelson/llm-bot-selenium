"""Exporter/HTTP/recording and WebDriver-double UNIT tests; not real browser evidence."""
import ast
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from triage.dag import DAG, Task, PythonSource
from triage.standalone import action, export_python, export_spec
from triage.standalone_demo import demo_dag
from triage.standalone_runtime import BOUNDARY, ReplayFailure, run, validate_spec
from test_browser_loop import browser_dag, manager, finished, FakeDriver, Element
from test_dag_server import backend, request

HOME = 'http://fixture:8080/'
DETAILS = 'http://fixture:8080/details.html'
URLS = [HOME, DETAILS]
REV = 'a' * 64


class ExportTests(unittest.TestCase):
    def test_dependencies_determine_order_even_with_scrambled_storage(self):
        dag = demo_dag(*URLS)
        scrambled = replace(dag, tasks=tuple(reversed(dag.tasks)))
        spec = export_spec(scrambled, REV, URLS)
        self.assertEqual([t['id'] for t in spec['tasks']], ['task-open', 'task-details'])
        self.assertEqual([t['depends_on'] for t in spec['tasks']], [[], ['task-open']])
        self.assertEqual([s['op'] for t in spec['tasks'] for s in t['steps']],
                         ['navigate', 'click', 'click', 'wait_visible', 'assert_text'])
        self.assertEqual(spec, export_spec(dag, REV, URLS))

    def test_missing_action_locator_urls_wait_and_final_assertion_reject(self):
        for key in ('op', 'id', 'tag', 'href', 'pre_url', 'post_url', 'wait'):
            dag = deepcopy(demo_dag(*URLS))
            del dag.tasks[1].params['replay']['steps'][1][key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                export_python(dag, REV, URLS)
        for op in ('script', 'scroll', 'observe', 'finish', 'read', 'shortcut', 'send_keys', 'execute_python'):
            dag = deepcopy(demo_dag(*URLS))
            dag.tasks[1].params['replay']['steps'][1]['op'] = op
            with self.subTest(op=op), self.assertRaises(ValueError):
                export_python(dag, REV, URLS)
        dag = deepcopy(demo_dag(*URLS))
        dag.tasks[2].params['replay']['steps'].pop()
        with self.assertRaisesRegex(ValueError, 'final visible assertion'):
            export_python(dag, REV, URLS)
        for key in ('url', 'wait', 'post_url'):
            dag = deepcopy(demo_dag(*URLS))
            del dag.tasks[1].params['replay']['steps'][0][key]
            with self.subTest(initial=key), self.assertRaises(ValueError): export_python(dag, REV, URLS)
        for unsupported in ({'frame': 'example'}, {'window': 'other'}, {'script': 'arbitrary()'}):
            dag = deepcopy(demo_dag(*URLS))
            dag.tasks[1].params['replay']['steps'][1].update(unsupported)
            with self.assertRaises(ValueError): export_python(dag, REV, URLS)

    def test_prompt_only_unapproved_sensitive_custom_and_unknown_tasks_reject(self):
        dag = demo_dag(*URLS)
        for task in (replace(dag.tasks[1], params={'prompt': 'Click something'}),
                     replace(dag.tasks[1], action='parallel'), replace(dag.tasks[1], action='mystery'),
                     replace(dag.tasks[1], kind='snippet'),
                     replace(dag.tasks[1], implementation=PythonSource('print("custom")', 'user', 'approved'))):
            invalid = replace(dag, tasks=(dag.tasks[0], task, *dag.tasks[2:]))
            with self.assertRaises(ValueError): export_python(invalid, REV, URLS)
        for field, value in (('synthetic', False), ('version', 'unknown')):
            invalid = deepcopy(dag)
            invalid.tasks[1].params['replay'][field] = value
            with self.assertRaises(ValueError): export_python(invalid, REV, URLS)
        for url in ('file:///tmp/a', 'https://user:pass@fixture/', 'https://fixture/?q=personal', 'https://fixture/password', 'https://fixture/%70ath'):
            with self.assertRaises(ValueError): export_python(dag, REV, [url])
        with self.assertRaises(ValueError): export_python(dag, 'old-revision', URLS)

    def test_parallel_branch_and_loop_reject_at_export_not_runtime(self):
        from triage.dag import LoopSpec
        branch = DAG('Branch', (
            Task('start', 'Start', 'start', kind='start', routes={'next': 'branch'}),
            Task('branch', 'Branch', 'condition', kind='branch', depends_on=('start',), routes={'yes': 'left', 'no': 'right'}, predicate={'input': 'n', 'operator': '>', 'threshold': 0, 'sample': 1}),
            Task('left', 'Left', 'application', depends_on=('branch',), routes={'next': 'end'}),
            Task('right', 'Right', 'application', depends_on=('branch',), routes={'next': 'end'}),
            Task('end', 'End', 'end', kind='end', depends_on=('left', 'right'))))
        loop = DAG('Loop', (
            Task('loop', 'Loop', 'loop', kind='loop', routes={'body': 'continue', 'done': 'end'}, loop=LoopSpec('for', 'i', 0, 1, 1, '<', 1, 'continue', 'continue', ('continue',))),
            Task('continue', 'Continue', 'loop-end', kind='continue', scope='loop'),
            Task('end', 'End', 'end', kind='end', depends_on=('loop',))))
        for dag in (branch, loop):
            with self.assertRaisesRegex(ValueError, 'Unsupported branch/loop/parallel/snippet'):
                export_python(dag, REV, URLS)

    def test_copied_single_file_runs_isolated_without_project_imports(self):
        source = export_python(demo_dag(*URLS), REV, URLS)
        tree = ast.parse(source)
        allowed = {'argparse', 'json', 'os', 're', 'signal', 'sys', 'threading', 'time', 'urllib', 'selenium'}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom): self.assertIn(node.module.split('.')[0], allowed)
            if isinstance(node, ast.Import):
                for alias in node.names: self.assertIn(alias.name.split('.')[0], allowed)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name): self.assertNotIn(node.func.id, ('exec', 'eval'))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'only_export.py'
            path.write_text(source)
            child = subprocess.run([sys.executable, '-I', str(path), '--check'], cwd=folder,
                                   env={'PATH': os.environ.get('PATH', ''), 'HOME': folder}, text=True, capture_output=True, timeout=10)
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertIn('browser not executed', child.stdout)
            self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_cli_exports_saved_revision_and_refuses_stale_or_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            saved, urls, output = root/'saved.py', root/'urls.json', root/'export.py'
            saved.write_text(demo_dag(*URLS).to_python())
            urls.write_text(json.dumps(URLS))
            revision = hashlib.sha256(saved.read_bytes()).hexdigest()
            command = [sys.executable, '-m', 'triage.standalone', str(saved), '--revision', revision,
                       '--urls', str(urls), '--output', str(output)]
            result = subprocess.run(command, text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('browser not executed', result.stdout)
            original = output.read_bytes()
            self.assertEqual(subprocess.run(command, capture_output=True, timeout=10).returncode, 2)
            self.assertEqual(output.read_bytes(), original)
            saved.write_text(replace(demo_dag(*URLS), name='New saved revision').to_python())
            result = subprocess.run(command, text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertIn('Stale canonical revision', result.stderr)
            self.assertEqual(output.read_bytes(), original)


class ReplayElement:
    def __init__(self, driver, kind, identity=''):
        self.driver, self.kind, self.identity = driver, kind, identity
    def is_displayed(self): return True
    def is_enabled(self): return True
    @property
    def tag_name(self): return 'a' if self.identity == 'open-details' else 'button'
    @property
    def text(self): return 'Synthetic replay complete' if self.driver.shown else ''
    def get_attribute(self, name):
        return {'data-sre-safe': 'true', 'href': DETAILS if self.identity == 'open-details' else None, 'type': 'button'}.get(name)
    def click(self):
        self.driver.clicks.append(self.identity)
        if self.identity == 'open-details': self.driver.current_url = DETAILS
        else: self.driver.shown = True
    def clear(self): self.driver.inputs.append('clear')
    def send_keys(self, value): self.driver.inputs.append(value)


class ReplayDriver:
    """UNIT double only, never real Selenium acceptance."""
    def __init__(self):
        self.current_url, self.window_handles, self.shown = 'about:blank', ['one'], False
        self.capabilities = {'browserName': 'MicrosoftEdge'}
        self.clicks, self.inputs, self.quits, self.commands = [], [], 0, []
        self.ambiguous, self.private, self.unsafe, self.missing = False, False, False, False
    def implicitly_wait(self, n): self.commands.append(('implicit', n))
    def set_page_load_timeout(self, n): pass
    def set_script_timeout(self, n): pass
    def execute_cdp_cmd(self, method, params): return {'arguments': ['--no-sandbox'] if self.unsafe else ['--headless=new']}
    def execute_script(self, script, *args):
        self.commands.append(script)
        if script == 'return document.readyState': return 'complete'
        if script == BOUNDARY: return not self.private
        return True
    def find_elements(self, by, selector):
        if selector == '[data-sre-observe]': return [ReplayElement(self, 'root')]
        if self.missing: return []
        identity = selector.split('"')[1]
        e = ReplayElement(self, 'result' if 'data-sre-result' in selector else 'action', identity)
        return [e, e] if self.ambiguous else [e]
    def get(self, url): self.current_url = url
    def quit(self): self.quits += 1


class RuntimeUnitTests(unittest.TestCase):
    def test_missing_locator_times_out_without_skipping_and_quits_unit_only(self):
        driver, clock = ReplayDriver(), [0.0]
        driver.missing = True
        def tick():
            clock[0] += .05
            return clock[0]
        with patch('triage.standalone_runtime.time.monotonic', side_effect=tick), patch('triage.standalone_runtime.time.sleep'), self.assertRaisesRegex(ReplayFailure, 'task-open/step-2: explicit wait'):
            run(export_spec(demo_dag(*URLS), REV, URLS), 'http://grid:4444', driver_factory=lambda *args: driver)
        self.assertEqual(driver.clicks, [])
        self.assertEqual(driver.quits, 1)

    def test_hard_spec_budgets_reject_before_driver_creation_unit_only(self):
        for mode in ('run', 'actions', 'task'):
            spec = export_spec(demo_dag(*URLS), REV, URLS)
            if mode == 'run': spec['run_timeout'] = 301
            if mode == 'task': spec['tasks'][0]['timeout'] = 0
            if mode == 'actions':
                spec['tasks'] = [spec['tasks'][0]]
                spec['tasks'][0]['steps'] = [action('navigate', HOME, HOME, url=HOME)] + [action('assert_text', HOME, HOME, id='status', text='Synthetic replay complete') for _ in range(100)]
            with self.subTest(mode=mode), self.assertRaises(ValueError): validate_spec(spec)

    def test_full_fixed_operation_trace_and_cleanup_unit_only(self):
        driver = ReplayDriver()
        run(export_spec(demo_dag(*URLS), REV, URLS), 'http://grid:4444', driver_factory=lambda *args: driver)
        self.assertEqual(driver.clicks, ['open-details', 'show-result'])
        self.assertEqual(driver.quits, 1)
        self.assertIn(('implicit', 0), driver.commands)

    def test_ambiguous_private_unsafe_and_unavailable_cdp_fail_closed_unit_only(self):
        for flag in ('ambiguous', 'private', 'unsafe', 'no_cdp'):
            d = ReplayDriver()
            if flag == 'no_cdp': d.execute_cdp_cmd = lambda *args: {}
            else: setattr(d, flag, True)
            with self.subTest(flag=flag), self.assertRaises(ReplayFailure):
                run(export_spec(demo_dag(*URLS), REV, URLS), 'http://grid:4444', driver_factory=lambda *args: d)
            self.assertEqual(d.quits, 1)
            self.assertFalse(d.clicks)

    def test_runtime_input_named_env_only_and_no_value_logging_unit_only(self):
        spec = export_spec(demo_dag(*URLS), REV, URLS)
        spec['tasks'][1]['steps'].insert(0, action('input', DETAILS, DETAILS, id='filter', env='SRE_REPLAY_INPUT_FILTER'))
        d = ReplayDriver()
        with patch.dict(os.environ, {'SRE_REPLAY_INPUT_FILTER': 'synthetic-filter'}):
            run(spec, 'http://grid:4444', driver_factory=lambda *args: d)
        self.assertEqual(d.inputs, ['clear', 'synthetic-filter'])
        self.assertNotIn('synthetic-filter', json.dumps(spec))
        d = ReplayDriver()
        with patch.dict(os.environ, {'SRE_REPLAY_INPUT_FILTER': 'secret-value'}), self.assertRaises(ReplayFailure) as error:
            run(spec, 'http://grid:4444', driver_factory=lambda *args: d)
        self.assertNotIn('secret-value', str(error.exception))
        self.assertEqual(d.quits, 1)

    def test_escape_window_and_raw_error_sanitized_unit_only(self):
        for mode in ('escape', 'window', 'error', 'cancel'):
            d = ReplayDriver()
            original = d.get
            def navigate(url):
                original(url)
                if mode == 'escape': d.current_url = 'https://unapproved.example/'
                if mode == 'window': d.window_handles = ['one', 'two']
                if mode == 'error': raise RuntimeError('SECRET_RAW_DOM_ERROR')
                if mode == 'cancel': raise KeyboardInterrupt()
            d.get = navigate
            with self.subTest(mode=mode), self.assertRaises(ReplayFailure) as error:
                run(export_spec(demo_dag(*URLS), REV, URLS), 'http://grid:4444', driver_factory=lambda *args: d)
            self.assertNotIn('SECRET_RAW_DOM_ERROR', str(error.exception))
            self.assertEqual(d.quits, 1)


    def test_noop_click_does_not_advance_or_repeat_unit_only(self):
        d = ReplayDriver()
        original = d.find_elements
        def elements(by, selector):
            rows = original(by, selector)
            for e in rows:
                if e.identity == 'show-result':
                    def noop(): d.clicks.append('show-result')
                    e.click = noop
            return rows
        d.find_elements = elements
        clock = [0.0]
        def tick(): clock[0] += .05; return clock[0]
        with patch('triage.standalone_runtime.time.monotonic', side_effect=tick), patch('triage.standalone_runtime.time.sleep'), self.assertRaisesRegex(ReplayFailure, 'task-details/step-1: explicit wait'):
            run(export_spec(demo_dag(*URLS), REV, URLS), 'http://grid:4444', driver_factory=lambda *args: d)
        self.assertEqual(d.clicks.count('show-result'), 1)
        self.assertEqual(d.quits, 1)

    def test_already_satisfied_click_is_not_repeated_unit_only(self):
        d = ReplayDriver(); d.shown = True
        with self.assertRaisesRegex(ReplayFailure, 'already satisfied; no click sent'):
            run(export_spec(demo_dag(*URLS), REV, URLS), 'http://grid:4444', driver_factory=lambda *args: d)
        self.assertNotIn('show-result', d.clicks)
        self.assertEqual(d.quits, 1)


class CaptureDriver(FakeDriver):
    """Existing recorder contract plus fixed replay guards. UNIT only."""
    window_handles = ['one']
    def execute_script(self, script, *args):
        if script == 'return window.top === window.self': return True
        if script == BOUNDARY or script.startswith('return !arguments[0].closest'): return True
        if script == 'return document.readyState': return 'complete'
        return super().execute_script(script, *args)
    def find_elements(self, by, selector):
        if selector == '[data-sre-result="errors"]': return [Element(self, 'result')]
        if selector == '[data-sre-action="show-errors"]': return [self.control()]
        if selector.endswith('[data-sre-action="show-errors"]'): return [self.control()]
        return super().find_elements(by, selector)
    def control(self):
        e = Element(self, 'action', 'show-errors')
        original = e.get_attribute
        e.get_attribute = lambda name: 'button' if name == 'type' else original(name)
        return e


class RecordedExportTests(unittest.TestCase):
    def test_actual_recorder_path_to_export_and_legacy_evidence_rejected_unit_only(self):
        dag = browser_dag()
        task = replace(dag.tasks[1], params={**dag.tasks[1].params, 'replay_capture': {'synthetic': True}})
        dag = replace(dag, tasks=(dag.tasks[0], task, dag.tasks[2]))
        with manager(CaptureDriver()) as (runs, _, revision):
            revision[0] = REV
            record = finished(runs, runs.start(dag, REV, task.task_id, True, False))
            self.assertEqual(record['status'], 'passed', record.get('reason'))
            source = export_python(dag, REV, runs.urls, [record])
            spec = export_spec(dag, REV, runs.urls, [record])
            self.assertEqual([s['op'] for s in spec['tasks'][0]['steps']], ['navigate', 'click', 'assert_text'])
            for forbidden in ('observation', 'proposal', 'frames', 'prompt', 'modelCalls', 'evidenceKind', 'Read release errors'):
                self.assertNotIn(forbidden, json.dumps(spec))
            self.assertNotIn('Choose the useful', source)
            for mutation in ('replay', 'locator', 'state', 'afterUrl', 'revision', 'status', 'wait'):
                invalid = deepcopy(record)
                if mutation == 'replay': del invalid['steps'][0]['replay']
                elif mutation == 'wait': del invalid['steps'][0]['replay']['wait']
                elif mutation in ('revision', 'status'): invalid[mutation] = 'stale-or-incomplete'
                else: invalid['steps'][0][mutation] = 'missing-or-unverified'
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    export_python(dag, REV, runs.urls, [invalid])
            invalid = deepcopy(record)
            invalid['steps'].append({**invalid['steps'][0], 'action': 'observe'})
            with self.assertRaises(ValueError): export_python(dag, REV, runs.urls, [invalid])


class HTTPExportTests(unittest.TestCase):
    def test_complete_recording_export_endpoint_uses_current_saved_task_unit_only(self):
        dag = browser_dag()
        dag = replace(dag, tasks=(dag.tasks[0], replace(dag.tasks[1], params={**dag.tasks[1].params, 'replay_capture': {'synthetic': True}}), dag.tasks[2]))
        with manager(CaptureDriver()) as (runs, _, revision), backend(dag, test_mode=True, recordings=runs.root) as (port, path, _):
            rev = request(port)[1]['revision']
            revision[0] = rev
            record = finished(runs, runs.start(dag, rev, 'browser-check', True, False))
            self.assertEqual(record['status'], 'passed')
            route = '/api/dag/export/selenium'
            headers = {'Content-Type': 'application/json', 'If-Match': rev}
            body = json.dumps({'runIds': [record['id']]})
            self.assertEqual(request(port, 'POST', body, headers, route)[0], 200)
            changed = replace(dag, name='Reviewed new revision')
            path.write_text(changed.to_python())
            headers['If-Match'] = request(port)[1]['revision']
            status, error = request(port, 'POST', body, headers, route)
            self.assertEqual(status, 422)
            self.assertIn('canonical revision', error['error'])

    def test_revision_origin_size_and_saved_definition_authority(self):
        with patch.dict(os.environ, {'SRE_BROWSER_URLS': json.dumps(URLS)}), backend(demo_dag(*URLS)) as (port, path, _):
            rev = request(port)[1]['revision']
            headers = {'Content-Type': 'application/json', 'If-Match': rev}
            route = '/api/dag/export/selenium'
            before = path.read_bytes()
            status, source = request(port, 'POST', '{"runIds":[]}', headers, route)
            self.assertEqual(status, 200)
            self.assertIn(b'SPEC = json.loads(', source)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(request(port, 'POST', '{"runIds":[]}', {**headers, 'If-Match': 'old'}, route)[0], 409)
            self.assertEqual(request(port, 'POST', '{}', {**headers, 'Origin': 'https://evil.example'}, route)[0], 403)
            self.assertEqual(request(port, 'POST', '{}', {**headers, 'Content-Length': '8193'}, route)[0], 413)
            self.assertEqual(request(port, 'POST', '{', headers, route)[0], 400)
            self.assertEqual(request(port, 'POST', '{"runIds":[],"definition":{}}', headers, route)[0], 400)
            self.assertEqual(request(port, 'POST', '{"runIds":[]}', {}, route)[0], 415)
            with patch('triage.standalone.export_python', side_effect=lambda *args: (path.write_text(replace(demo_dag(*URLS), name='External change').to_python()), 'discard')[1]):
                self.assertEqual(request(port, 'POST', '{"runIds":[]}', headers, route)[0], 409)

    def test_unsupported_saved_workflow_is_visible_422(self):
        with backend(browser_dag()) as (port, _, _):
            rev = request(port)[1]['revision']
            status, error = request(port, 'POST', '{"runIds":[]}', {'Content-Type': 'application/json', 'If-Match': rev}, '/api/dag/export/selenium')
            self.assertEqual(status, 422)
            self.assertIn('prompt-only', error['error'])


if __name__ == '__main__':
    unittest.main()
