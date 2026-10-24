"""Real HTTP API and worker tests with a simulated driver, not live Edge evidence."""
from dataclasses import replace
import json
import os
from pathlib import Path
from triage.dag import load_python
from threading import Event
import unittest
from unittest.mock import patch

from triage.browser_loop import BrowserRuns, task_config
from test_browser_loop import browser_dag, FakeDriver
from test_dag_server import backend, request, commit


def public_dag():
    dag = browser_dag()
    return replace(dag, tasks=tuple(replace(t, params={**t.params, 'target': 'https://or9.ca/',
        'prompt': 'Read-only public homepage check', 'browser': {'mode': 'read-only-or9'}})
        if t.task_id == 'browser-check' else t for t in dag.tasks))


class UIGridTests(unittest.TestCase):
    def test_edge_ui_example_uses_the_real_inert_dag_parser(self):
        dag = load_python((Path(__file__).resolve().parents[1] / 'examples/edge_grid_dag.py').read_text())
        self.assertEqual(dag.name, 'Edge Grid browser tests')
        self.assertEqual(dag.tasks[1].params['browser'], {'mode': 'read-only-or9'})

    def test_public_mode_requires_exact_owner_approved_url_and_no_video(self):
        task = public_dag().tasks[1]
        for urls in (set(), {'http://127.0.0.1:8080/'}):
            with self.assertRaises(ValueError): task_config(task, urls)
        self.assertEqual(task_config(task, {'https://or9.ca/'})[2], {'mode': 'read-only-or9'})
        for params in ({**task.params, 'target': 'https://other.example/'},
                       {**task.params, 'browser': {'mode': 'read-only-or9', 'capture': True}}):
            with self.assertRaises(ValueError): task_config(replace(task, params=params), {'https://or9.ca/', 'https://other.example/'})

    def test_ui_load_edit_save_run_poll_history_and_read_only_cleanup(self):
        driver, done = FakeDriver(), Event()
        driver.title = 'Public homepage'
        original = BrowserRuns.run
        def worker(self, *args):
            try: return original(self, *args)
            finally: done.set()
        with patch.dict(os.environ, {'SELENIUM_GRID_URL': 'http://grid:4444', 'SRE_BROWSER_URLS': '["https://or9.ca/"]'}), patch('triage.grid.status', return_value={'ready': True, 'nodes': 1, 'browsers': ['MicrosoftEdge'], 'edgeAvailable': True}), patch('triage.browser_loop.grid_status', return_value={'ready': True}), patch('triage.browser_loop.create_driver', return_value=driver), patch('triage.browser_loop.propose') as model, patch.object(BrowserRuns, 'run', worker), backend(browser_dag(), test_mode=True) as (port, _, _):
            code, health = request(port, path='/api/test/status')
            self.assertEqual(code, 200)
            self.assertTrue(health['grid']['edgeAvailable'])
            self.assertEqual(health['approvedUrls'], ['https://or9.ca/'])
            loaded = request(port)[1]
            code, saved = commit(port, loaded['revision'], public_dag().to_spec())
            self.assertEqual(code, 200)
            headers = {'Content-Type': 'application/json', 'If-Match': saved['revision']}
            payload = {'nodeId': 'browser-check', 'consent': True, 'video': True}
            self.assertEqual(request(port, 'POST', json.dumps(payload), headers, '/api/browser/runs')[0], 400)
            payload['video'] = False
            self.assertEqual(request(port, 'POST', json.dumps({**payload, 'consent': False}), headers, '/api/browser/runs')[0], 400)
            code, queued = request(port, 'POST', json.dumps(payload), headers, '/api/browser/runs')
            self.assertEqual(code, 202)
            self.assertTrue(done.wait(5))
            code, record = request(port, path='/api/browser/runs/' + queued['id'])
            self.assertEqual(code, 200)
            self.assertEqual(record['status'], 'passed')
            self.assertEqual(record['frames'], [])
            self.assertEqual(record['steps'], [])
            self.assertEqual(record['modelCalls'], 0)
            self.assertNotIn('video', record)
            self.assertEqual(record['triage']['events'][0]['url'], 'https://or9.ca/')
            self.assertEqual(request(port, path='/api/browser/runs')[1][0]['id'], queued['id'])
            model.assert_not_called()
            self.assertEqual(driver.gets, ['https://or9.ca/'])
            self.assertEqual(driver.clicks, [])
            self.assertEqual(driver.frame_calls, 0)
            self.assertEqual(driver.quits, 1)

    def test_browser_startup_error_is_visible_without_claiming_navigation(self):
        class SessionNotCreatedException(Exception): pass
        done = Event()
        original = BrowserRuns.run
        def worker(self, *args):
            try: return original(self, *args)
            finally: done.set()
        with patch.dict(os.environ, {'SELENIUM_GRID_URL': 'http://grid:4444', 'SRE_BROWSER_URLS': '["https://or9.ca/"]'}), patch('triage.browser_loop.grid_status', return_value={'ready': True}), patch('triage.browser_loop.create_driver', side_effect=SessionNotCreatedException('untrusted secret')), patch.object(BrowserRuns, 'run', worker), backend(public_dag(), test_mode=True) as (port, _, _):
            revision = request(port)[1]['revision']
            code, queued = request(port, 'POST', json.dumps({'nodeId': 'browser-check', 'consent': True, 'video': False}), {'Content-Type': 'application/json', 'If-Match': revision}, '/api/browser/runs')
            self.assertEqual(code, 202)
            self.assertTrue(done.wait(5))
            record = request(port, path='/api/browser/runs/' + queued['id'])[1]
            self.assertEqual(record['status'], 'failed')
            self.assertIn('Edge could not start', record['reason'])
            self.assertNotIn('untrusted secret', json.dumps(record))
            self.assertEqual(record['triage']['events'], [])
