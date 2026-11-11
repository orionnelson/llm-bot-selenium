"""Synthetic UNIT evidence only: fake Airflow HTTP and a stdlib child, no live Grid."""
import ast
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from triage.airflow_replay import AirflowClient, AirflowError, ReplayRegistry, from_env
from triage.airflow_worker import execute_replay
from triage.standalone_demo import demo_dag
from test_dag_server import backend, request

URLS = ['http://fixture:8080/', 'http://fixture:8080/details.html']
REV = 'a' * 64
CONFIG = {'grid': 'http://grid:4444', 'browser': 'edge', 'isolation': 'browser'}


class FakeHTTP:
    """Transport seam, never connects to Airflow or Selenium."""
    def __init__(self):
        self.calls, self.variables, self.runs = [], {}, {}
        self.state, self.loaded, self.retries, self.lose_trigger = 'queued', True, 0, False

    def __call__(self, method, path, body, token):
        self.calls.append((method, path, body))
        if path == '/auth/token':
            return {'access_token': 'server-only-token'}
        if path == '/api/v2/variables' and method == 'POST':
            if body['key'] in self.variables:
                raise AirflowError('Conflict', 409)
            self.variables[body['key']] = body['value']
            return body
        if '/variables/' in path:
            self.variables[path.rsplit('/', 1)[1]] = body['value']
            return body
        if '/dagSources/sre_replay_' in path:
            artifact_id = path.rsplit('sre_replay_', 1)[1]
            return {'content': (self.dags / ('sre_replay_' + artifact_id + '.py')).read_text()}
        artifact_id = path.split('/dags/sre_replay_')[1].split('/')[0]
        if path.endswith('/tasks'):
            return {'tasks': [{'task_id': 'replay_chain', 'retries': self.retries}]}
        if '/dagRuns?' in path:
            return {'dag_runs': [{'state': self.state} for _ in self.runs]}
        if path.endswith('/dagRuns') and method == 'POST':
            self.runs[body['dag_run_id']] = body
            if self.lose_trigger:
                raise AirflowError('Lost response')
            return {'state': 'queued'}
        if path.endswith('/taskInstances'):
            return {'task_instances': [{'task_id': 'replay_chain', 'state': self.state, 'try_number': 1}]}
        if path.endswith('/xcomEntries/replay_result'):
            return {'value': {'steps': [{'task': 'task-open', 'step': 1, 'state': 'passed', 'reason': 'DO NOT EXPOSE'}]}}
        if '/dagRuns/' in path:
            return {'state': self.state}
        if method == 'PATCH':
            return body
        return {'tags': [{'name': 'artifact:' + artifact_id}] if self.loaded else [], 'max_active_runs': 1, 'timetable_summary': 'None'}


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dags = self.root / 'dags'
        self.dags.mkdir()
        self.http = FakeHTTP()
        self.http.dags = self.dags
        self.client = AirflowClient('http://airflow:8080', lambda: ('server-user', 'SERVER_SECRET'), self.http)
        self.registry = ReplayRegistry(self.root / 'registry', self.dags, self.client, CONFIG)

    def save(self):
        return self.registry.save(demo_dag(*URLS), REV, URLS, [])

    def test_immutable_portable_bundle_and_public_metadata(self):
        value = self.save()
        self.assertEqual(self.save(), value)
        deployed = self.dags / ('sre_replay_' + value['id'] + '.py')
        source = deployed.read_text()
        ast.parse(source)
        for setting in ('schedule=None', 'catchup=False', 'is_paused_upon_creation=True', 'max_active_runs=1', 'retries=0', 'from airflow.sdk import DAG, task'):
            self.assertIn(setting, source)
        self.assertIn('def validate_spec', source)
        self.assertNotIn('from triage', source)
        self.assertEqual(value['tasks'], ['task-open', 'task-details'])
        self.assertNotIn('grid', json.dumps(self.registry.listing()))
        self.assertNotIn('SERVER_SECRET', source)
        other = self.registry.save(demo_dag(*URLS), 'b' * 64, URLS, [])
        self.assertNotEqual(other['id'], value['id'])
        deployed.write_text(source + '\n# changed')
        with self.assertRaisesRegex(ValueError, 'integrity'):
            self.registry.start(value['id'])

    def test_loaded_contract_and_manual_only_run(self):
        value = self.save()
        self.http.loaded = False
        with self.assertRaisesRegex(ValueError, 'loaded'):
            self.registry.start(value['id'])
        self.http.loaded, self.http.retries = True, 1
        with self.assertRaisesRegex(ValueError, 'contract'):
            self.registry.start(value['id'])
        self.http.retries = 0
        run = self.registry.start(value['id'])
        triggers = [c for c in self.http.calls if c[0] == 'POST' and c[1].endswith('/dagRuns')]
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0][2]['conf'], {})
        self.assertTrue(triggers[0][2]['drain_dag'])
        self.assertFalse(any(c[0] == 'PATCH' and c[2] == {'is_paused': False} for c in self.http.calls))
        self.assertEqual(run['revision'], REV)
        with self.assertRaisesRegex(ValueError, 'active'):
            self.registry.start(value['id'])
        restarted = ReplayRegistry(self.registry.root, self.dags, self.client, CONFIG)
        with self.assertRaisesRegex(ValueError, 'active'):
            restarted.start(value['id'])

    def test_revision_change_during_export_publishes_nothing(self):
        with self.assertRaisesRegex(ValueError, 'revision changed'):
            self.registry.save(demo_dag(*URLS), REV, URLS, [], revision_check=lambda: 'b'*64)
        self.assertEqual(list(self.dags.iterdir()), [])

    def test_lost_trigger_response_reconciles_without_duplicate(self):
        value = self.save()
        self.http.lose_trigger = True
        with self.assertRaises(AirflowError):
            self.registry.start(value['id'])
        self.assertEqual(self.registry.active()['state'], 'submitting')
        with self.assertRaises(ValueError):
            self.registry.start(value['id'])
        self.assertEqual(self.registry.status(value['id'])['state'], 'queued')
        self.assertEqual(len(self.http.runs), 1)

    def test_stop_is_marker_not_state_patch_and_terminal_repauses(self):
        value = self.save()
        self.registry.start(value['id'])
        self.assertEqual(self.registry.stop(value['id'])['state'], 'stopping')
        self.assertEqual(len(self.http.variables), 8)
        self.assertEqual(self.registry.stop(value['id'])['state'], 'stopping')
        self.assertEqual(self.registry.status(value['id'])['state'], 'stopping')
        self.assertFalse(any(c[0] == 'PATCH' and '/taskInstances' in c[1] for c in self.http.calls))
        self.http.state = 'failed'
        result = self.registry.status(value['id'])
        self.assertEqual(result['state'], 'failed')
        self.assertIsNone(self.registry.active())
        self.assertNotIn('DO NOT EXPOSE', json.dumps(self.registry.logs(value['id'])))
        self.assertTrue(any(c[0] == 'PATCH' and c[2] == {'is_paused': True} for c in self.http.calls))

    def test_http_consent_revision_paths_and_disabled_boundary(self):
        with patch.dict(os.environ, {'SRE_AIRFLOW_REPLAY_ENABLED': '0'}):
            self.assertIsNone(from_env())
            with backend(demo_dag(*URLS)) as (port, _, __):
                self.assertEqual(request(port, path='/api/airflow/artifacts')[0], 503)
        with patch.dict(os.environ, {'SRE_BROWSER_URLS': json.dumps(URLS)}), backend(demo_dag(*URLS), airflow_replay=self.registry) as (port, _, __):
            revision = request(port)[1]['revision']
            headers = {'Content-Type': 'application/json', 'If-Match': revision}
            route = '/api/airflow/artifacts'
            payload = {'runIds': [], 'reviewed': True, 'synthetic': True}
            for changed in ({'reviewed': False}, {'synthetic': False}, {'path': '/tmp/injected.py'}, {'code': 'print(1)'}):
                self.assertEqual(request(port, 'POST', json.dumps(dict(payload, **changed)), headers, route)[0], 409)
            self.assertEqual(request(port, 'POST', json.dumps(payload), dict(headers, **{'If-Match': REV}), route)[0], 409)
            code, artifact = request(port, 'POST', json.dumps(payload), headers, route)
            self.assertEqual(code, 201)
            self.assertEqual(artifact['revision'], revision)
            self.assertEqual(request(port, 'GET', headers={'Host': 'evil.example'}, path=route)[0], 403)
            self.assertEqual(request(port, 'POST', json.dumps({'confirmed': True, 'conf': {'url': 'http://evil/'}}), headers, route+'/'+artifact['id']+'/run')[0], 409)
            self.assertEqual(request(port, 'GET', path=route+'/not-a-hash/status')[0], 409)
            self.assertEqual(request(port, 'POST', ' '*9000, headers, route)[0], 413)
            with patch('triage.dag_server.snapshot', side_effect=AssertionError('Replay must not reload source')), patch('triage.airflow_replay.export_python', side_effect=AssertionError('Replay must not regenerate')):
                self.assertEqual(request(port, 'POST', json.dumps({'confirmed': True}), headers, route+'/'+artifact['id']+'/run')[0], 202)
                self.assertEqual(request(port, path=route+'/'+artifact['id']+'/status')[1]['state'], 'queued')

    def test_missing_worker_dependency_reaches_sanitized_app_logs(self):
        value = self.save()
        run = self.registry.start(value['id'])
        self.http.state = 'failed'
        original = self.client.request
        def request(method, path, body=None):
            if path.endswith('/xcomEntries/replay_result'):
                return {'value': {'steps': [{'task': 'startup', 'step': 0, 'state': 'failed',
                        'reason': 'Selenium dependency unavailable in replay environment', 'raw': 'SECRET'}]}}
            return original(method, path, body)
        with patch.object(self.client, 'request', side_effect=request):
            result = self.registry.status(value['id'])
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(result['runId'], run['runId'])
        logs = self.registry.logs(value['id'])['logs']
        self.assertEqual(logs, ['startup/step-0: failed · Selenium dependency unavailable in replay environment'])
        self.assertNotIn('SECRET', json.dumps(result))

    def test_transport_exception_and_provider_secrets_are_sanitized(self):
        def broken(*args):
            raise RuntimeError('password=SERVER_SECRET response body')
        client = AirflowClient('http://airflow:8080', lambda: ('user', 'SERVER_SECRET'), broken)
        with self.assertRaises(AirflowError) as error:
            client.request('GET', '/dags')
        self.assertNotIn('SERVER_SECRET', str(error.exception))


class WorkerTests(unittest.TestCase):
    def sdk(self, get, values):
        sdk = types.ModuleType('airflow.sdk')
        sdk.Variable = types.SimpleNamespace(get=get)
        ti = types.SimpleNamespace(xcom_push=lambda **kw: values.append(kw['value']))
        sdk.get_current_context = lambda: {'run_id': 'replay__unit', 'ti': ti}
        return patch.dict(sys.modules, {'airflow': types.ModuleType('airflow'), 'airflow.sdk': sdk})

    def test_child_startup_crash_is_visible_without_forwarding_raw_output(self):
        values = []
        with self.sdk(lambda *a, **k: 'false', values):
            with self.assertRaisesRegex(RuntimeError, 'stopped or failed'):
                execute_replay('import sys; print("SECRET", file=sys.stderr); sys.exit(2)',
                               CONFIG['grid'], 'edge', 'browser', 'a'*64)
        self.assertEqual(values[0]['steps'], [{'task': 'startup', 'step': 0, 'state': 'failed',
                          'reason': 'replay process exited before first browser step'}])
        self.assertNotIn('SECRET', json.dumps(values))

    def test_prestart_stop_does_not_create_subprocess(self):
        values = []
        with self.sdk(lambda *a, **k: 'true', values), patch('subprocess.Popen') as start:
            with self.assertRaisesRegex(RuntimeError, 'before browser'):
                execute_replay('invalid executable', CONFIG['grid'], 'edge', 'browser', 'a'*64)
            start.assert_not_called()
        self.assertEqual(values[0]['state'], 'stopped')

    def test_signal_during_prestart_read_never_launches_child(self):
        import signal
        handlers = {}
        def install(sig, fn): handlers[sig] = fn; return signal.SIG_DFL
        def get(*args, **kwargs): handlers[signal.SIGTERM](); return 'false'
        with self.sdk(get, []), patch('signal.signal', side_effect=install), patch('subprocess.Popen') as start:
            with self.assertRaisesRegex(RuntimeError, 'before browser'):
                execute_replay('invalid', CONFIG['grid'], 'edge', 'browser', 'a'*64)
            start.assert_not_called()

    def test_running_stop_sigterms_child_and_waits_for_cleanup_unit_only(self):
        values, polls = [], [0]
        def get(key, **kwargs):
            if key.endswith('requested'):
                return 'false'
            polls[0] += 1
            return 'true' if polls[0] > 1 else 'false'
        with tempfile.TemporaryDirectory() as root:
            cleaned = Path(root) / 'cleaned'
            # Stdlib process double: no browser session or real replay evidence.
            child = ('import signal,time\nfrom pathlib import Path\n'
                     'def stop(*args):\n Path(' + repr(str(cleaned)) + ').write_text("cleanup")\n raise SystemExit(2)\n'
                     'signal.signal(signal.SIGTERM,stop)\nwhile True: time.sleep(.01)\n')
            with self.sdk(get, values):
                with self.assertRaisesRegex(RuntimeError, 'stopped or failed'):
                    execute_replay(child, CONFIG['grid'], 'edge', 'browser', 'a'*64)
            self.assertEqual(cleaned.read_text(), 'cleanup')
            self.assertEqual(values[0]['state'], 'stopped')


if __name__ == '__main__':
    unittest.main()
