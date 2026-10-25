import json
from dataclasses import replace
from pathlib import Path
from threading import Event, Thread
from http.client import HTTPConnection
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError

from triage.dag import DAG, Task
from triage.test_codegen import MODEL, generate
from triage.grid import create_driver, endpoint, status, smoke
from test_dag_server import backend, request, commit

SOURCE = 'def run(inputs, context=None):\n    return {"branch": "yes" if inputs["i"] > 3 else "no"}\n'


def saved():
    return DAG('Saved test', (Task('saved', 'Saved', 'condition', kind='branch',
        routes={'yes': 'yes', 'no': 'no'}, predicate={'input': 'i', 'operator': '>', 'threshold': 3, 'sample': 5}),
        Task('yes', 'Yes', 'end', kind='end', depends_on=('saved',)),
        Task('no', 'No', 'end', kind='end', depends_on=('saved',))))


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.resident_running, self.qwen_status = True, 'unloaded'

    def model_api(self, path, payload=None):
        if path == '/v1/models':
            return {'data': [{'id': MODEL, 'status': {'value': self.qwen_status}}, {'id': 'resident', 'status': {'value': 'loaded' if self.resident_running else 'unloaded'}}]}
        if path == '/models/unload':
            if payload['model'] == MODEL: self.qwen_status = 'unloaded'
            else: self.resident_running = False
            return {'status': 'ok'}
        if path == '/models/load':
            self.qwen_status = 'loaded'
            return {'status': 'ok'}
        return {'model': MODEL, 'choices': [{'finish_reason': 'stop', 'message': {'content': SOURCE}}]}

    def test_real_provider_protocol_unloads_loads_and_returns_review_only_source(self):
        with patch('triage.test_codegen.smol', side_effect=self.model_api) as api:
            value = generate(saved(), 'saved', 'Compare input i to 3')
        self.assertEqual(value, {'source': SOURCE, 'model': MODEL, 'review': 'pending', 'mode': 'test', 'executed': False})
        self.assertEqual([c.args[0] for c in api.call_args_list], ['/v1/models', '/models/unload', '/v1/models', '/models/load', '/v1/models', '/v1/chat/completions'])
        self.assertEqual(api.call_args_list[3].args[1], {'model': MODEL})
        context = json.loads(api.call_args_list[-1].args[1]['messages'][1]['content'])
        self.assertEqual(set(context), {'action', 'predicate', 'instructions'})
        self.assertNotIn('params', context)
        self.assertNotIn('implementation', context)

    def test_async_unload_is_observed_before_reloading_same_model(self):
        state = ['loaded']
        def api(path, payload=None):
            if path == '/v1/models':
                current = state[0]
                if current == 'unloading': state[0] = 'unloaded'
                return {'data': [{'id': MODEL, 'status': {'value': current}}]}
            if path == '/models/unload':
                state[0] = 'unloading'
                return {'success': True}
            if path == '/models/load':
                if state[0] != 'unloaded': raise ValueError('model is already running')
                state[0] = 'loaded'
                return {'success': True}
            return {'model': MODEL, 'choices': [{'finish_reason': 'stop', 'message': {'content': SOURCE}}]}
        with patch('triage.test_codegen.smol', side_effect=api), patch('triage.test_codegen.time.sleep') as pause:
            self.assertEqual(generate(saved(), 'saved', 'Synthetic comparison')['source'], SOURCE)
        pause.assert_called_once_with(1)

    def test_invalid_request_or_unsaved_task_never_calls_model(self):
        for node_id, instructions in [('missing', 'Compare'), ('saved', ''), ('saved', 'x' * 12001)]:
            with patch('triage.test_codegen.smol') as api, self.assertRaises(ValueError):
                generate(saved(), node_id, instructions)
            api.assert_not_called()

    def test_wrong_model_truncated_fenced_and_invalid_source_rejected(self):
        variants = [
            {'model': 'other', 'choices': []},
            {'model': MODEL, 'choices': [{'finish_reason': 'length', 'message': {'content': SOURCE}}]},
            {'model': MODEL, 'choices': [{'finish_reason': 'stop', 'message': {'content': '```python\n' + SOURCE + '```'}}]},
            {'model': MODEL, 'choices': [{'finish_reason': 'stop', 'message': {'content': 'def wrong(): pass'}}]},
        ]
        for variant in variants:
            def api(path, payload=None):
                return variant if path == '/v1/chat/completions' else self.model_api(path, payload)
            with patch('triage.test_codegen.smol', side_effect=api), self.assertRaises(ValueError):
                generate(saved(), 'saved', 'Compare i')

    def test_generated_top_level_source_is_inert_not_a_python_import(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'executed'
            candidate = f'open({str(marker)!r}, "w").write("bad")\n' + SOURCE
            def api(path, payload=None):
                if path == '/v1/chat/completions':
                    return {'model': MODEL, 'choices': [{'finish_reason': 'stop', 'message': {'content': candidate}}]}
                return self.model_api(path, payload)
            with patch('triage.test_codegen.smol', side_effect=api):
                self.assertEqual(generate(saved(), 'saved', 'Synthetic comparison')['source'], candidate)
            self.assertFalse(marker.exists())  # Syntax validation is explicitly NOT a safety sandbox.

    def test_http_opt_in_and_saved_canonical_task_boundary(self):
        with backend(saved()) as (port, path, _):
            before = path.read_bytes()
            with patch('triage.test_codegen.generate') as api:
                self.assertEqual(request(port, 'POST', '{}', {'Content-Type': 'application/json'}, '/api/python/generate')[0], 503)
            api.assert_not_called()
            self.assertEqual(request(port, path='/api/test/status')[0], 503)
            self.assertEqual(path.read_bytes(), before)

    def test_enabled_http_does_not_forward_browser_config_or_persist_candidate(self):
        with backend(saved(), test_mode=True) as (port, path, _):
            before = path.read_bytes()
            body = {'nodeId': 'saved', 'instructions': 'Synthetic comparison', 'config': {'token': 'must-not-forward'}}
            with patch('triage.test_codegen.generate', return_value={'source': SOURCE, 'model': MODEL, 'review': 'pending', 'executed': False}) as api:
                code, result = request(port, 'POST', json.dumps(body), {'Content-Type': 'application/json'}, '/api/python/generate')
                self.assertEqual(code, 200)
                self.assertEqual(api.call_args.args, (saved(), 'saved', 'Synthetic comparison'))
                self.assertFalse(result['executed'])
            self.assertEqual(path.read_bytes(), before)
            body['nodeId'] = 'unsaved'
            self.assertEqual(request(port, 'POST', json.dumps(body), {'Content-Type': 'application/json'}, '/api/python/generate')[0], 409)
            with patch.dict('os.environ', {}, clear=True):
                status_value = request(port, path='/api/test/status')[1]
                self.assertEqual(status_value['grid']['ready'], False)
                self.assertEqual(status_value['execution'], 'consented-test-browser-actions')
                self.assertFalse(status_value['generatedPythonExecution'])

    def test_enabled_http_provider_failure_and_bad_inputs_do_not_save(self):
        with backend(saved(), test_mode=True) as (port, path, _):
            before = path.read_bytes()
            body = json.dumps({'nodeId': 'saved', 'instructions': 'Synthetic comparison'})
            with patch('triage.test_codegen.generate', side_effect=URLError('blocked')):
                self.assertEqual(request(port, 'POST', body, {'Content-Type': 'application/json'}, '/api/python/generate')[0], 502)
            for body in ('[]', '{}', '{'):
                self.assertEqual(request(port, 'POST', body, {'Content-Type': 'application/json'}, '/api/python/generate')[0], 400)
            self.assertEqual(path.read_bytes(), before)


    def test_canonical_change_during_generation_discards_candidate_and_releases_lock(self):
        for change in ('commit', 'external', 'invalid', 'missing', 'unchanged'):
            with self.subTest(change=change), backend(saved(), test_mode=True) as (port, path, _):
                entered, release, responses = Event(), Event(), []
                candidate = {'source': SOURCE, 'model': MODEL, 'review': 'pending', 'executed': False}
                def slow(*args):
                    entered.set()
                    if not release.wait(5):
                        raise TimeoutError('Test did not release model double')
                    return candidate
                body = json.dumps({'nodeId': 'saved', 'instructions': 'Synthetic comparison'})
                def generate_request():
                    return request(port, 'POST', body, {'Content-Type': 'application/json'}, '/api/python/generate')
                with patch('triage.test_codegen.generate', side_effect=slow):
                    worker = Thread(target=lambda: responses.append(generate_request()))
                    worker.start()
                    try:
                        self.assertTrue(entered.wait(2))
                        original = request(port)[1]
                        changed = replace(saved(), tasks=(replace(saved().tasks[0],
                            predicate={**saved().tasks[0].predicate, 'threshold': 9}), *saved().tasks[1:]))
                        if change == 'commit':
                            self.assertEqual(commit(port, original['revision'], changed.to_spec())[0], 200)
                        elif change == 'external':
                            path.write_text(changed.to_python())
                        elif change == 'invalid':
                            path.write_text('not a DAG')
                        elif change == 'missing':
                            path.unlink()
                        current = path.read_bytes() if path.exists() else None
                    finally:
                        release.set()
                        worker.join(5)
                    self.assertFalse(worker.is_alive())
                    self.assertEqual(len(responses), 1)
                    status, value = responses[0]
                    self.assertEqual(status, 200 if change == 'unchanged' else 409 if change in ('commit', 'external') else 502)
                    if change == 'unchanged':
                        self.assertEqual(value, candidate)
                    else:
                        self.assertNotIn('source', value)
                    self.assertEqual(path.read_bytes() if path.exists() else None, current)
                    # A rejected response must not leave the single-generation lock held.
                    path.write_text(saved().to_python())
                    self.assertEqual(generate_request()[0], 200)

    def test_slow_generation_does_not_block_dag_reads_and_second_generation_is_busy(self):
        entered, release = Event(), Event()
        def slow(*args):
            entered.set()
            release.wait(5)
            return {'source': SOURCE, 'model': MODEL, 'review': 'pending', 'executed': False}
        with backend(saved(), test_mode=True) as (port, _, _), patch('triage.test_codegen.generate', side_effect=slow):
            body = json.dumps({'nodeId': 'saved', 'instructions': 'Synthetic comparison'})
            worker = Thread(target=lambda: request(port, 'POST', body, {'Content-Type': 'application/json'}, '/api/python/generate'))
            worker.start()
            try:
                self.assertTrue(entered.wait(2))
                connection = HTTPConnection('127.0.0.1', port, timeout=1)
                connection.request('GET', '/api/dag')
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                response.read()
                connection.close()
                self.assertEqual(request(port, 'POST', body, {'Content-Type': 'application/json'}, '/api/python/generate')[0], 429)
            finally:
                release.set()
                worker.join(5)


class GridTests(unittest.TestCase):
    def test_credential_or_path_endpoints_are_rejected(self):
        for url in ('file:///etc/passwd', 'http://user:pass@grid:4444', 'http://grid:4444/private', 'http://grid:4444/?token=x'):
            with self.assertRaises(ValueError):
                endpoint(url)
        self.assertEqual(endpoint('http://selenium:4444/'), 'http://selenium:4444')

    def test_remote_constructor_uses_native_binary_without_sandbox_bypass(self):
        try:
            import selenium
        except ImportError:
            self.skipTest('Selenium package required; this test is not an actual Grid session')
        with patch('selenium.webdriver.Remote') as remote:
            self.assertIs(create_driver('http://selenium:4444'), remote.return_value)
        options = remote.call_args.kwargs['options']
        self.assertEqual(options.binary_location, '/opt/microsoft/msedge/msedge')
        self.assertEqual(options.to_capabilities()['browserName'], 'MicrosoftEdge')
        self.assertEqual(options.arguments, ['--headless=new'])
        self.assertEqual(remote.call_args.kwargs['command_executor'], 'http://selenium:4444')
        self.assertEqual(remote.call_args.kwargs['client_config'].timeout, 30)

    def test_smoke_quits_isolated_session_on_pass_and_failure(self):
        for unsafe in (False, True):
            driver = Mock(title='Synthetic Grid check', capabilities={'browserName': 'MicrosoftEdge'})
            driver.execute_cdp_cmd.return_value = {'arguments': ['--no-sandbox'] if unsafe else ['--headless=new']}
            with patch('triage.grid.status', return_value={'ready': True}), patch('triage.grid.create_driver', return_value=driver):
                if unsafe:
                    with self.assertRaisesRegex(ValueError, 'sandbox disabled'):
                        smoke('http://grid:4444')
                    driver.get.assert_not_called()
                else:
                    self.assertEqual(smoke('http://grid:4444')['status'], 'passed')
                    self.assertTrue(driver.get.call_args.args[0].startswith('data:text/html,'))
            driver.quit.assert_called_once()

    def test_not_ready_grid_never_creates_a_session(self):
        with patch('triage.grid.status', return_value={'ready': False}), patch('triage.grid.create_driver') as create:
            with self.assertRaises(ValueError):
                smoke('http://grid:4444')
        create.assert_not_called()


class PublicGridTests(unittest.TestCase):
    def driver(self):
        driver = Mock(title='Orion', current_url='https://or9.ca/',
                      capabilities={'browserName': 'MicrosoftEdge'})
        driver.execute_script.return_value = 'https://or9.ca/'
        driver.execute_cdp_cmd.return_value = {'arguments': ['--headless=new']}
        driver.find_element.return_value.is_displayed.return_value = True
        return driver

    def test_or9_is_explicit_read_only_and_quits(self):
        driver = self.driver()
        with patch('triage.grid.status', return_value={'ready': True}), patch('triage.grid.create_driver', return_value=driver):
            result = smoke('http://grid:4444', or9=True)
        self.assertEqual(result['status'], 'passed')
        driver.get.assert_called_once_with('https://or9.ca/')
        driver.find_element.assert_called_once_with('tag name', 'body')
        driver.find_element.return_value.click.assert_not_called()
        driver.save_screenshot.assert_not_called()
        driver.quit.assert_called_once()

    def test_public_failures_never_report_success_and_always_quit(self):
        for failure in ('redirect', 'empty-title', 'hidden-body', 'navigation', 'wrong-browser', 'unsafe', 'error-document'):
            with self.subTest(failure=failure):
                driver = self.driver()
                if failure == 'error-document': driver.execute_script.return_value = 'chrome-error://chromewebdata/'
                if failure == 'redirect': driver.current_url = 'https://other.example/'
                if failure == 'empty-title': driver.title = ' '
                if failure == 'hidden-body': driver.find_element.return_value.is_displayed.return_value = False
                if failure == 'navigation': driver.get.side_effect = RuntimeError('network blocked')
                if failure == 'wrong-browser': driver.capabilities = {'browserName': 'chrome'}
                if failure == 'unsafe': driver.execute_cdp_cmd.return_value = {'arguments': ['--no-sandbox']}
                with patch('triage.grid.status', return_value={'ready': True}), patch('triage.grid.create_driver', return_value=driver):
                    with self.assertRaises((ValueError, RuntimeError)):
                        smoke('http://grid:4444', or9=True)
                driver.quit.assert_called_once()
                if failure in ('wrong-browser', 'unsafe'): driver.get.assert_not_called()
