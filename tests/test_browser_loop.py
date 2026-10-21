from contextlib import contextmanager
from dataclasses import replace
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile
from threading import Event, Lock
import unittest
from unittest.mock import patch
import zlib

from triage.browser_loop import BrowserRuns, DEFAULT_URLS, MASK, OBSERVE, observe, propose, safe_url, task_config
from triage.dag import PythonSource, load_python
from test_dag_server import backend, request


def browser_dag():
    return load_python((Path(__file__).resolve().parents[1] / 'examples/browser_dag.py').read_text())


def png(shown=False):
    def chunk(kind, value):
        return struct.pack('>I', len(value)) + kind + value + struct.pack('>I', zlib.crc32(kind+value))
    pixels = (b'\0' + (b'\0\x80\0' if shown else b'\x30\x40\x50')*2)*2
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 2, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b'')


class Element:
    def __init__(self, driver, kind, identity=''):
        self.driver, self.kind, self.identity = driver, kind, identity

    def is_displayed(self):
        return self.driver.shown if self.kind == 'result' else True

    def is_enabled(self):
        return not (self.identity == 'show-errors' and self.driver.shown)

    @property
    def text(self):
        return self.driver.result_text if self.kind == 'result' else 'View errors'

    def find_elements(self, by, selector):
        return [Element(self.driver, 'result')] if selector == '[data-sre-result="errors"]' else []

    @property
    def tag_name(self): return 'button' if self.identity == 'show-errors' else 'a'

    def get_attribute(self, name):
        if name == 'data-sre-safe': return 'false' if self.driver.invalid_control else 'true'
        if name == 'data-sre-action': return self.identity
        return DEFAULT_URLS[1] if name == 'href' else None

    def click(self):
        self.driver.clicks.append(self.identity)
        if self.identity == 'open-details': self.driver.current_url = DEFAULT_URLS[1]
        if self.driver.escape: self.driver.current_url = 'https://unapproved.example/'
        self.driver.shown = True

    @property
    def screenshot_as_png(self):
        assert self.driver.masked, 'Frame must be redacted before capture'
        self.driver.frame_calls += 1
        if self.driver.frame_calls == self.driver.fail_frame: raise OSError('Synthetic frame failure')
        return png(self.driver.shown)


class FakeDriver:
    """Simulated WebDriver, NOT real browser evidence. Real DOM integration is separately gated."""
    def __init__(self):
        self.current_url, self.shown, self.masked = DEFAULT_URLS[0], False, False
        self.clicks, self.gets, self.quits, self.frame_calls = [], [], 0, 0
        self.fail_frame, self.escape, self.unsafe, self.invalid_control = -1, False, False, False
        self.label, self.result_text = 'View errors', 'Errors: 0'
        self.session_id = 'must-not-leak-webdriver-session'

    def get(self, url): self.gets.append(url); self.current_url = url
    def quit(self): self.quits += 1
    def set_page_load_timeout(self, seconds): pass
    def set_script_timeout(self, seconds): pass
    def set_window_size(self, width, height): pass
    def execute_cdp_cmd(self, method, args): return {'arguments': ['--no-sandbox'] if self.unsafe else ['--headless=new']}
    def find_element(self, by, selector): return Element(self, 'root')
    def find_elements(self, by, selector):
        if selector == '[data-sre-observe]': return [Element(self, 'root')]
        if 'data-sre-action="show-errors"' in selector: return [Element(self, 'action', 'show-errors')]
        if 'data-sre-action="open-details"' in selector: return [Element(self, 'action', 'open-details')]
        return []
    def execute_script(self, script, *args):
        if script == MASK: self.masked = True; return Element(self, 'style')
        if script == 'arguments[0].remove()': self.masked = False; return None
        assert script == OBSERVE, 'No generated script may run'
        return {'text': 'Release dashboard ' + self.label + (' '+self.result_text if self.shown else ''), 'result': self.result_text if self.shown else None,
                'candidates': ([] if self.shown else [{'id': 'show-errors', 'label': self.label, 'tag': 'button', 'href': None}]) +
                              [{'id': 'open-details', 'label': 'Open details', 'tag': 'a', 'href': DEFAULT_URLS[1]}]}


def choice(goal, observation):
    return {'action': 'click', 'candidate': 'show-errors', 'evidence': observation['evidence']}


@contextmanager
def manager(driver=None, planner=choice):
    driver = driver or FakeDriver()
    revision = ['revision-1']
    with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'SELENIUM_GRID_URL': 'http://selenium:4444', 'SRE_BROWSER_URLS': json.dumps(DEFAULT_URLS)}), patch('triage.browser_loop.grid_status', return_value={'ready': True}), patch('triage.browser_loop.propose', side_effect=planner):
        runs = BrowserRuns(Path(directory), Lock(), lambda: revision[0], driver_factory=lambda url: driver, evidence_kind='simulated')
        try:
            yield runs, driver, revision
        finally:
            for event in list(runs.active.values()): event.set()
            if runs.generation_lock.acquire(timeout=10): runs.generation_lock.release()


def finished(runs, result):
    if not runs.generation_lock.acquire(timeout=10): raise AssertionError('Run did not terminate')
    runs.generation_lock.release()
    return runs.read(result['id'])


class BrowserLoopTests(unittest.TestCase):
    def test_full_dag_to_observe_propose_click_record_and_reusable_session(self):
        with manager() as (runs, driver, _):
            record = finished(runs, runs.start(browser_dag(), 'revision-1', 'browser-check', True, False))
            self.assertEqual(record['status'], 'passed')
            self.assertEqual(record['evidenceKind'], 'simulated')
            self.assertEqual(driver.clicks, ['show-errors'])
            self.assertEqual(driver.quits, 1)
            self.assertFalse(driver.masked)
            self.assertEqual(record['verifiedResult'], 'Errors: 0')
            self.assertEqual(record['steps'][0]['state'], 'verified')
            self.assertEqual(record['steps'][0]['proposal']['evidence'], record['steps'][0]['observation']['evidence'])
            self.assertEqual([e['action'] for e in record['triage']['events']], ['navigate', 'click'])
            self.assertEqual(len(record['frames']), 2)
            self.assertEqual(len(record['frameTimesMs']), 2)
            self.assertLessEqual(*record['frameTimesMs'])
            self.assertNotIn(driver.session_id, json.dumps(record))
            self.assertNotIn('NOT_A_REAL_PASSWORD', json.dumps(record))
            for url in record['frames']:
                path = runs.root / record['id'] / url.rsplit('/', 1)[1]
                self.assertEqual(path.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')
                self.assertEqual(path.stat().st_mode & 0o077, 0)

    def test_consent_policy_and_url_rejected_before_any_browser(self):
        for url in ('file:///etc/passwd', 'http://user:password@host/', 'https://example.com/?token=x', 'http://host/#secret', 'http://host/token%3DFAKE', 'http://host/bearer%20FAKE', 'http://host\\evil/'):
            with self.assertRaises(ValueError): safe_url(url)
        with manager() as (runs, driver, _):
            for consent in (False, 'true', 1):
                with self.assertRaises(ValueError): runs.start(browser_dag(), 'revision-1', 'browser-check', consent, False)
            dag = browser_dag()
            task = dag.tasks[1]
            invalid = replace(dag, tasks=(dag.tasks[0], replace(task, params={**task.params, 'target': 'https://unapproved.example/'}), dag.tasks[2]))
            with self.assertRaises(ValueError): runs.start(invalid, 'revision-1', 'browser-check', True, False)
            self.assertEqual(driver.gets, [])
            self.assertEqual(list(runs.root.iterdir()), [])

    def test_stale_page_or_canonical_definition_stops_before_click(self):
        for stale_dag in (False, True):
            driver = FakeDriver()
            with manager(driver) as (runs, _, revision):
                def changed(goal, observation):
                    if stale_dag: revision[0] = 'new-revision'
                    else: driver.label = 'Changed control'
                    return choice(goal, observation)
                with patch('triage.browser_loop.propose', side_effect=changed):
                    record = finished(runs, runs.start(browser_dag(), 'revision-1', 'browser-check', True, False))
                self.assertEqual(record['status'], 'blocked')
                self.assertEqual(driver.clicks, [])
                self.assertEqual(driver.quits, 1)

    def test_private_observation_root_is_rejected_before_frames_or_actions(self):
        driver = FakeDriver()
        original = driver.execute_script
        driver.execute_script = lambda script,*args: {'private': True} if script == OBSERVE else original(script,*args)
        with manager(driver) as (runs, _, _):
            record = finished(runs, runs.start(browser_dag(), 'revision-1', 'browser-check', True, False))
            self.assertEqual(record['status'], 'blocked')
            self.assertEqual(driver.frame_calls, 0)
            self.assertEqual(driver.clicks, [])
            self.assertEqual(driver.quits, 1)

    def test_target_permission_is_rechecked_immediately_before_click(self):
        driver = FakeDriver()
        def changed(goal, observation):
            driver.invalid_control = True
            return choice(goal, observation)
        with manager(driver, changed) as (runs, _, _):
            record = finished(runs, runs.start(browser_dag(), 'revision-1', 'browser-check', True, False))
            self.assertEqual(record['status'], 'blocked')
            self.assertEqual(driver.clicks, [])
            self.assertEqual(driver.quits, 1)

    def test_model_finish_does_not_manufacture_a_success(self):
        with manager(planner=lambda goal, o: {'action': 'finish', 'candidate': None, 'evidence': o['evidence']}) as (runs, driver, _):
            record = finished(runs, runs.start(browser_dag(), 'revision-1', 'browser-check', True, False))
            self.assertEqual(record['status'], 'blocked')
            self.assertNotIn('verifiedResult', record)
            self.assertEqual(driver.clicks, [])

    def test_screenshot_failure_before_action_blocks_and_after_action_marks_uncertain(self):
        for call in (1, 2):
            driver = FakeDriver(); driver.fail_frame = call
            with manager(driver) as (runs, _, _):
                record = finished(runs, runs.start(browser_dag(), 'revision-1', 'browser-check', True, False))
                self.assertEqual(record['status'], 'recording_failed')
                self.assertEqual(len(driver.clicks), call-1)
                self.assertFalse(driver.masked)
                self.assertEqual(driver.quits, 1)
                if call == 2: self.assertEqual(record['steps'][0]['state'], 'performed')

    def test_unapproved_navigation_and_sandbox_disabled_browser_never_pass(self):
        for unsafe in (False, True):
            driver = FakeDriver(); driver.unsafe, driver.escape = unsafe, not unsafe
            with manager(driver) as (runs, _, _):
                record = finished(runs, runs.start(browser_dag(), 'revision-1', 'browser-check', True, False))
                self.assertEqual(record['status'], 'blocked')
                self.assertEqual(driver.quits, 1)
                if unsafe: self.assertEqual(driver.gets, [])

    def test_generated_python_is_not_an_execution_path(self):
        with tempfile.TemporaryDirectory() as directory, manager() as (runs, driver, _):
            marker = Path(directory) / 'executed'
            dag = browser_dag(); task = replace(dag.tasks[1], implementation=PythonSource(f'open({str(marker)!r}, "w").write("bad")'))
            dag = replace(dag, tasks=(dag.tasks[0], task, dag.tasks[2]))
            record = finished(runs, runs.start(dag, 'revision-1', 'browser-check', True, False))
            self.assertEqual(record['status'], 'passed')
            self.assertFalse(marker.exists())

    def test_cancel_and_single_run_capacity_during_model_wait(self):
        entered, release = Event(), Event()
        def slow(goal, observation):
            entered.set(); release.wait(5); return choice(goal, observation)
        with manager(planner=slow) as (runs, driver, _):
            queued = runs.start(browser_dag(), 'revision-1', 'browser-check', True, False)
            try:
                self.assertTrue(entered.wait(2))
                with self.assertRaises(BlockingIOError): runs.start(browser_dag(), 'revision-1', 'browser-check', True, False)
                self.assertTrue(runs.cancel(queued['id'])['cancellation_requested'])
                self.assertEqual(runs.read(queued['id'])['status'], 'cancelling')
            finally: release.set()
            self.assertEqual(finished(runs, queued)['status'], 'cancelled')
            self.assertEqual(driver.clicks, [])
            self.assertEqual(driver.quits, 1)

    def test_record_capacity_preserves_existing_files_and_no_browser_starts(self):
        with manager() as (runs, driver, _):
            for i in range(20): (runs.root / str(i)).mkdir()
            with self.assertRaises(OSError): runs.start(browser_dag(), 'revision-1', 'browser-check', True, False)
            self.assertEqual(len(list(runs.root.iterdir())), 20)
            self.assertEqual(driver.gets, [])

    @unittest.skipUnless(shutil.which('ffmpeg'), 'Optional ffmpeg is not installed; video acceptance not claimed')
    def test_actual_ffmpeg_export_of_simulated_action_frames(self):
        with manager() as (runs, _, _):
            record = finished(runs, runs.start(browser_dag(), 'revision-1', 'browser-check', True, True))
            self.assertEqual(record['status'], 'passed')
            self.assertEqual(record['video']['kind'], 'action-frames')
            data = (runs.root / record['id'] / 'actions.webm').read_bytes()
            self.assertTrue(data.startswith(b'\x1aE\xdf\xa3'))
            self.assertGreater(len(data), 100)

    def test_model_proposals_are_grounded_not_free_selectors_or_scripts(self):
        observation = {'evidence': 'a'*64, 'candidates': [{'id': 'show-errors'}]}
        variants = [[], {'action': 'click', 'candidate': 'invented', 'evidence': 'a'*64},
                    {'action': 'click', 'candidate': 'show-errors', 'evidence': 'stale'},
                    {'action': 'script', 'candidate': 'alert(1)', 'evidence': 'a'*64},
                    {'action': 'click', 'candidate': 'show-errors', 'evidence': 'a'*64, 'python': 'bad'}]
        for value in variants:
            with patch('triage.browser_loop.complete', return_value=json.dumps(value)), self.assertRaises(ValueError): propose('Read errors', observation)
        with patch('triage.browser_loop.complete', return_value=json.dumps({'action': 'click', 'candidate': 'show-errors', 'evidence': 'a'*64})) as model:
            self.assertEqual(propose('Read errors', observation)['candidate'], 'show-errors')
            self.assertTrue(model.call_args.kwargs['json_mode'])

    def test_restart_is_interrupted_and_never_automatically_resumed(self):
        with manager() as (runs, _, _):
            record = finished(runs, runs.start(browser_dag(), 'revision-1', 'browser-check', True, False))
            path = runs.root / record['id'] / 'manifest.json'
            record['status'] = 'running'; path.write_text(json.dumps(record))
            self.assertEqual(runs.read(record['id'])['status'], 'interrupted')


class BrowserHTTPTests(unittest.TestCase):
    def test_disabled_consent_revision_and_arbitrary_url_override_rejected(self):
        with backend(browser_dag()) as (port, _, _):
            self.assertEqual(request(port, path='/api/browser/runs')[0], 503)
            self.assertEqual(request(port, 'POST', '{}', {'Content-Type': 'application/json'}, '/api/browser/runs')[0], 503)
        with backend(browser_dag(), test_mode=True) as (port, _, _):
            revision = request(port)[1]['revision']
            body = {'nodeId': 'browser-check', 'consent': True, 'video': False}
            self.assertEqual(request(port, 'POST', json.dumps(body), {'Content-Type': 'application/json'}, '/api/browser/runs')[0], 409)
            body['url'] = 'https://unapproved.example/'
            self.assertEqual(request(port, 'POST', json.dumps(body), {'Content-Type': 'application/json', 'If-Match': revision}, '/api/browser/runs')[0], 400)
            self.assertEqual(request(port, 'POST', '{}', {'Origin': 'https://evil.example'}, '/api/browser/runs')[0], 403)
            self.assertEqual(request(port, path='/api/browser/runs/../secret')[0], 404)

    def test_async_run_recording_and_private_asset_routes(self):
        driver, entered, release, completed = FakeDriver(), Event(), Event(), Event()
        original = BrowserRuns.run
        def worker(self, *args):
            try: return original(self, *args)
            finally: completed.set()
        def slow(goal, observation): entered.set(); release.wait(5); return choice(goal, observation)
        with patch('triage.browser_loop.BrowserRuns.run', worker), patch.dict(os.environ, {'SELENIUM_GRID_URL': 'http://selenium:4444'}), patch('triage.browser_loop.create_driver', return_value=driver), patch('triage.browser_loop.grid_status', return_value={'ready': True}), patch('triage.browser_loop.propose', side_effect=slow), backend(browser_dag(), test_mode=True) as (port, path, _):
            revision = request(port)[1]['revision']
            body = json.dumps({'nodeId': 'browser-check', 'consent': True, 'video': False})
            code, queued = request(port, 'POST', body, {'Content-Type': 'application/json', 'If-Match': revision}, '/api/browser/runs')
            self.assertEqual(code, 202)
            try:
                self.assertTrue(entered.wait(2))
                code, record = request(port, path='/api/browser/runs/'+queued['id'])
                self.assertEqual(code, 200)
                self.assertEqual(record['status'], 'running')
                self.assertEqual(request(port)[0], 200)
                frame = record['frames'][0]
                self.assertEqual(request(port, path=frame)[0], 200)
                self.assertEqual(request(port, path='/api/browser/runs/'+queued['id']+'/manifest.json')[0], 404)
                self.assertEqual(request(port, 'POST', path='/api/browser/runs/'+queued['id']+'/cancel')[0], 202)
            finally: release.set()
            self.assertTrue(completed.wait(5))
            self.assertEqual(driver.quits, 1)
            self.assertEqual(request(port, path='/api/browser/runs/'+queued['id'])[1]['status'], 'cancelled')


class RealGridBrowserLoopTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('RUN_GRID_BROWSER_LOOP') == '1', 'Real Grid+Qwen acceptance needs explicit opt-in, deployed private fixture and sandbox-capable node')
    def test_actual_grid_page_model_action_and_recording(self):
        with tempfile.TemporaryDirectory() as directory:
            runs = BrowserRuns(Path(directory), Lock(), lambda: 'integration-revision')
            queued = runs.start(browser_dag(), 'integration-revision', 'browser-check', True, False)
            self.assertTrue(runs.generation_lock.acquire(timeout=600), 'Browser/model run exceeded acceptance budget')
            runs.generation_lock.release()
            record = runs.read(queued['id'])
            self.assertEqual(record['status'], 'passed', record.get('error'))
            self.assertGreaterEqual(record['modelCalls'], 1)
            self.assertTrue(record['steps'])
            self.assertEqual(record['verifiedResult'], 'Errors: 0')
            self.assertEqual(record['evidenceKind'], 'selenium-grid')
            text = json.dumps([s['observation'] for s in record['steps']])
            self.assertNotIn('FAKE_PRIVATE_VALUE', text)
            self.assertNotIn('NOT_A_REAL_PASSWORD', text)
