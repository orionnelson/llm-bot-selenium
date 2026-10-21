from contextlib import contextmanager
from dataclasses import replace
from http.client import HTTPConnection
from http.server import HTTPServer
import json
from pathlib import Path
import tempfile
import subprocess
import sys
from threading import Thread
import unittest
from unittest.mock import patch

from triage.dag import DAG, Task, PythonSource, LoopSpec, load_python
from triage.dag_server import handler, snapshot, LIMIT


def definition():
    return DAG('Backend authored', (
        Task('start', 'Begin', 'start', kind='start', routes={'next': 'finish'}),
        Task('finish', 'Finished', 'end', kind='end', depends_on=('start',)),
    ))


@contextmanager
def backend(dag=None):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        path = root / 'workflow.py'
        path.write_text((dag or definition()).to_python())
        assets = root / 'dist'
        assets.mkdir()
        (assets / 'index.html').write_text('<title>DAG editor</title>')
        server = HTTPServer(('127.0.0.1', 0), handler(path, assets.resolve()))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server.server_port, path, assets
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


def request(port, method='GET', body=None, headers=None, path='/api/dag'):
    connection = HTTPConnection('127.0.0.1', port, timeout=10)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    data = response.read()
    connection.close()
    return response.status, json.loads(data) if response.getheader('Content-Type') == 'application/json' else data


def commit(port, revision, spec):
    return request(port, 'PUT', json.dumps(spec), {'Content-Type': 'application/json', 'If-Match': revision})


class DAGServerTests(unittest.TestCase):
    def test_python_authored_definition_is_served_without_a_canvas(self):
        with backend() as (port, path, _):
            status, value = request(port)
            self.assertEqual(status, 200)
            self.assertEqual(value['definition'], definition().to_spec())
            self.assertEqual(value['plan'], {'root': ['start', 'finish'], 'bodies': {}, 'execution': 'not started'})
            self.assertEqual(load_python(value['python']), definition())
            self.assertNotIn('position', value['definition']['tasks'][0])
            # A valid external author edit is reflected, not replaced with a UI template.
            path.write_text(replace(definition(), name='Python changed').to_python())
            self.assertEqual(request(port)[1]['definition']['name'], 'Python changed')

    def test_commit_returns_canonical_definition_and_persists_python(self):
        with backend() as (port, path, _):
            value = request(port)[1]
            draft = replace(definition(), name='Reviewed change')
            status, saved = commit(port, value['revision'], draft.to_spec())
            self.assertEqual(status, 200)
            self.assertEqual(load_python(path.read_text()), draft)
            self.assertEqual(saved, json.loads(json.dumps(snapshot(path))))
            self.assertNotEqual(value['revision'], saved['revision'])
            self.assertEqual(list(path.parent.glob('tmp*')), [])

    def test_invalid_and_stale_commits_preserve_canonical_file(self):
        with backend() as (port, path, _):
            value = request(port)[1]
            before = path.read_bytes()
            invalid = definition().to_spec()
            invalid['tasks'][1]['depends_on'] = []
            self.assertEqual(commit(port, value['revision'], invalid)[0], 400)
            self.assertEqual(commit(port, 'old-revision', definition().to_spec())[0], 409)
            self.assertEqual(path.read_bytes(), before)
            path.write_text(replace(definition(), name='Another writer').to_python())
            self.assertEqual(commit(port, value['revision'], definition().to_spec())[0], 409)
            self.assertEqual(load_python(path.read_text()).name, 'Another writer')

    def test_malformed_requests_and_unknown_fields_fail_closed(self):
        with backend() as (port, path, _):
            revision = request(port)[1]['revision']
            before = path.read_bytes()
            for invalid in (None, [], {'version': 'sre-dag/v1', 'name': 'Bad', 'tasks': [42]}, {**definition().to_spec(), 'positions': {}}):
                self.assertEqual(commit(port, revision, invalid)[0], 400)
            self.assertEqual(request(port, 'PUT', '{', {'Content-Type': 'application/json', 'If-Match': revision})[0], 400)
            self.assertEqual(request(port, 'PUT', '{}')[0], 415)
            self.assertEqual(request(port, 'PUT', '{}', {'Content-Type': 'application/json', 'Content-Length': str(LIMIT + 1)})[0], 413)
            self.assertEqual(path.read_bytes(), before)

    def test_cross_origin_and_dns_rebinding_cannot_read_or_write(self):
        with backend() as (port, path, _):
            before = path.read_bytes()
            for headers in ({'Origin': 'https://evil.example'}, {'Host': 'evil.example'}):
                self.assertEqual(request(port, headers=headers)[0], 403)
                self.assertEqual(request(port, 'PUT', '{}', headers)[0], 403)
            self.assertEqual(path.read_bytes(), before)

    def test_no_filesystem_or_execution_endpoint(self):
        with backend() as (port, path, assets):
            self.assertEqual(request(port, path='/')[0], 200)
            (assets / 'leak.py').symlink_to(path)
            for url in ('/../workflow.py', '/%2e%2e/workflow.py', '/leak.py', '/api/run'):
                self.assertEqual(request(port, path=url)[0], 404)
            self.assertEqual(request(port, path='/api/dag?path=/etc/passwd')[1]['definition']['name'], 'Backend authored')
            (assets / 'index.html').unlink()
            (assets / 'index.html').symlink_to(path)
            self.assertEqual(request(port, path='/')[0], 404)
            self.assertEqual(request(port, 'HEAD', path='/workflow.py')[0], 405)

    def test_invalid_server_python_is_not_executed_or_replaced(self):
        with backend() as (port, path, _):
            marker = path.parent / 'executed'
            path.write_text(f'open({str(marker)!r}, "w").write("bad")')
            self.assertEqual(request(port)[0], 422)
            self.assertFalse(marker.exists())

    def test_persistence_failure_does_not_destroy_definition(self):
        with backend() as (port, path, _):
            before = path.read_bytes()
            with patch('triage.dag_server.os.replace', side_effect=OSError('disk unavailable')):
                self.assertEqual(commit(port, request(port)[1]['revision'], definition().to_spec())[0], 503)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(path.parent.glob('tmp*')), [])

    def test_inert_source_and_scoped_loop_survive_backend_roundtrip(self):
        loop = LoopSpec('for', 'i', 0, 3, 1, '<', 10, 'body', 'continue', ('body', 'continue'))
        dag = DAG('Loop', (
            Task('loop', 'For', 'loop', kind='loop', routes={'body': 'body', 'done': 'end'}, loop=loop),
            Task('body', 'Read', 'application', scope='loop', routes={'next': 'continue'}, implementation=PythonSource('raise RuntimeError("never executed")')),
            Task('continue', 'Continue', 'loop-end', kind='continue', scope='loop', depends_on=('body',)),
            Task('end', 'End', 'end', kind='end', depends_on=('loop',)),
        ))
        with backend(dag) as (port, path, _):
            value = request(port)[1]
            self.assertEqual(value['plan']['bodies']['loop'], ['body', 'continue'])
            self.assertEqual(commit(port, value['revision'], value['definition'])[0], 200)
            self.assertEqual(load_python(path.read_text()), dag)

    def test_branch_join_plan_preserves_both_routes_not_execution(self):
        dag = DAG('Branch join', (
            Task('branch', 'Choose', 'condition', kind='branch', routes={'yes': 'a', 'no': 'b'}, predicate={'input': 'errors', 'operator': '>', 'threshold': 0, 'sample': 1}),
            Task('a', 'A', 'application', depends_on=('branch',), routes={'next': 'join'}),
            Task('b', 'B', 'application', depends_on=('branch',), routes={'next': 'join'}),
            Task('join', 'Join', 'end', kind='end', depends_on=('a', 'b')),
        ))
        with backend(dag) as (port, _, _):
            value = request(port)[1]
            self.assertEqual(value['plan']['root'], ['branch', 'a', 'b', 'join'])
            self.assertEqual(value['definition']['tasks'][0]['routes'], {'yes': 'a', 'no': 'b'})
            self.assertEqual(value['plan']['execution'], 'not started')

    def test_cli_refuses_to_create_a_definition_from_missing_state(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / 'missing.py'
            result = subprocess.run([sys.executable, '-m', 'triage.dag_server', '--dag', str(missing), '--port', '0'], capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Server DAG is missing or invalid', result.stderr)
            self.assertFalse(missing.exists())
