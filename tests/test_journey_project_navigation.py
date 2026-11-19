"""Reported project-name qualifier and guarded new-page navigation regressions."""
import json
import os
from pathlib import Path
import tempfile
from threading import Event, Lock
import unittest
from unittest.mock import Mock, patch

from triage import journey as controller
from triage.browser_loop import BrowserRuns, BrowserBlocked
from triage.journey import action_completed, click_target, start_journey, OBSERVE_PUBLIC
from triage.public_browser import PublicRequests
from test_journey import Driver, PUBLIC

REQUEST = 'Click on Drivers Licence Scanner Project'
LABEL = 'Drivers Licence Scanner IAM OpenCV'
DESTINATION = 'https://or9.ca/blog/opencv-update/'


def observation(url='https://or9.ca/work'):
    return {'url': url, 'documentUri': url, 'title': 'Public project', 'text': 'Projects Drivers Licence Scanner',
            'facts': [], 'articles': [], 'candidates': [
                {'id': 'scanner', 'kind': 'control', 'label': LABEL, 'href': '/blog/opencv-update/', 'target': '_blank'},
                {'id': 'news', 'kind': 'control', 'label': 'Security News', 'href': '#news'}]}


class ProjectNameTests(unittest.TestCase):
    def test_descriptive_project_suffix_keeps_the_full_named_target(self):
        self.assertTrue(action_completed(REQUEST, [{'action': 'click', 'label': LABEL}]))
        self.assertEqual([c['id'] for c in click_target(REQUEST, observation())], ['scanner'])
        self.assertFalse(action_completed(REQUEST, [{'action': 'click', 'label': 'Security News'}]))
        self.assertFalse(action_completed(REQUEST, [{'action': 'click', 'label': 'Drivers Licence Editor'}]))

    def test_earlier_project_word_remains_identifying(self):
        request = 'Click Project Orion Scanner Project'
        self.assertFalse(action_completed(request, [{'action': 'click', 'label': 'Orion Scanner'}]))
        self.assertTrue(action_completed(request, [{'action': 'click', 'label': 'Project Orion Scanner'}]))

    def test_project_only_does_not_match_arbitrary_controls(self):
        with self.assertRaisesRegex(BrowserBlocked, 'not observed'):
            click_target('Click Project', observation())

    def test_exact_label_preference_and_ambiguity_still_apply(self):
        obs = observation()
        obs['candidates'].append({'id': 'exact', 'kind': 'control', 'label': 'Drivers Licence Scanner Project', 'href': '/exact'})
        self.assertEqual([c['id'] for c in click_target(REQUEST, obs)], ['exact'])
        obs['candidates'][-1]['label'] = LABEL + ' alternate'
        with self.assertRaisesRegex(BrowserBlocked, 'ambiguous'):
            click_target(REQUEST, obs)

    def test_negative_target_remains_excluded(self):
        with self.assertRaisesRegex(BrowserBlocked, 'not observed'):
            click_target(REQUEST + ' but not Drivers Licence Scanner', observation())


class GuardSetupTests(unittest.TestCase):
    def test_constructor_failure_closes_socket_and_receiver(self):
        from queue import Queue, Empty
        import websocket
        from threading import Thread
        class Socket:
            def __init__(self): self.queue = Queue(); self.closed = False
            def recv(self):
                try: return self.queue.get(timeout=.05)
                except Empty: raise websocket.WebSocketTimeoutException()
            def close(self): self.closed = True; self.queue.put('')
        socket = Socket(); threads = []
        def thread(*args, **kwargs):
            t = Thread(*args, **kwargs); threads.append(t); return t
        def call(method, *args, **kwargs):
            if method == 'Target.attachToTarget': return {'sessionId': 'initial'}
            if method == 'Target.setAutoAttach': raise ValueError('unsupported command')
            return {}
        driver = Mock(); driver.capabilities = {'se:cdp': 'ws://synthetic'}
        driver.execute_cdp_cmd.return_value = {'targetInfo': {'type': 'page', 'targetId': 'initial-target'}}
        with patch('websocket.create_connection', return_value=socket), patch('triage.public_browser.Thread', side_effect=thread), patch.object(PublicRequests, 'call', side_effect=call):
            with self.assertRaisesRegex(ValueError, 'unsupported command'): PublicRequests(driver)
        self.assertTrue(socket.closed); self.assertTrue(threads)
        self.assertTrue(all(not t.is_alive() for t in threads))

    def test_send_failures_mark_receiver_disconnected_and_reject_ready_target(self):
        guard = PublicRequests.__new__(PublicRequests)
        guard.closed = False; guard.disconnected = False; guard.allowed = {}; guard.blocked = []
        guard.lock = Lock(); ready = Event(); ready.set(); guard.guarded_targets = {'target': ready}; guard.target_errors = {}
        guard.ws = Mock(); guard.ws.recv.return_value = json.dumps({'method': 'Fetch.requestPaused', 'sessionId': 'new', 'params': {'requestId': 'r', 'request': {'url': 'https://or9.ca/'}}})
        guard.send = Mock(side_effect=OSError('connection lost'))
        with patch('triage.public_browser.socket.getaddrinfo', return_value=PUBLIC): guard.receive()
        self.assertTrue(guard.disconnected); self.assertEqual(guard.send.call_count, 2)
        driver = Mock(); driver.execute_cdp_cmd.return_value = {'targetInfo': {'targetId': 'target'}}
        with self.assertRaisesRegex(ValueError, 'request guard'): guard.wait_for_current_target(driver)

    def test_filter_acknowledgement_precedes_resume(self):
        guard = PublicRequests.__new__(PublicRequests)
        guard.call = Mock(); guard.target_errors = {}
        ready = Event(); guard.guard_attached_page('new-session', 'new-target', ready)
        methods = [c.args[0] for c in guard.call.call_args_list]
        self.assertEqual(methods[0], 'Fetch.enable')
        self.assertEqual(methods[-1], 'Runtime.runIfWaitingForDebugger')
        self.assertTrue(ready.is_set())
        self.assertEqual(guard.target_errors, {})
        self.assertTrue(all(c.kwargs['session'] == 'new-session' for c in guard.call.call_args_list))

    def test_guard_failure_does_not_resume_new_page(self):
        guard = PublicRequests.__new__(PublicRequests)
        guard.call = Mock(side_effect=ValueError('filter rejected')); guard.target_errors = {}
        ready = Event(); guard.guard_attached_page('new-session', 'new-target', ready)
        self.assertFalse(ready.is_set())
        self.assertEqual(guard.target_errors, {'new-target': 'ValueError'})
        self.assertNotIn('Runtime.runIfWaitingForDebugger', [c.args[0] for c in guard.call.call_args_list])


class NewPageDriver(Driver):
    def __init__(self, extra=1, destination=DESTINATION):
        super().__init__(); self.window_handles = ['original']; self.current_window_handle = 'original'
        self.clicks = 0; self.extra = extra; self.destination = destination
        self.switch_to = Mock(); self.switch_to.window.side_effect = self.switch
        self.title = 'Public project'

    def switch(self, handle):
        self.current_window_handle = handle; self.current_url = self.destination

    def execute_script(self, script, *args):
        if script == OBSERVE_PUBLIC:
            value = observation(self.current_url)
            if self.current_window_handle != 'original':
                value['text'] = 'Drivers Licence Scanner project destination loaded'
            return value
        return None

    def find_element(self, *_):
        driver = self
        class Link:
            def is_displayed(self): return True
            def is_enabled(self): return True
            def click(self):
                driver.clicks += 1
                driver.window_handles.extend('new-' + str(i) for i in range(driver.extra))
        return Link()


class NewPageWorkerTests(unittest.TestCase):
    def run_worker(self, driver, guard):
        def propose(instruction, obs):
            return {'action': 'click', 'candidate': 'scanner', 'evidence': obs['evidence'],
                    'python': 'def run(browser):\n    browser.click("scanner", ' + json.dumps(obs['evidence']) + ')'}
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'SELENIUM_GRID_URL': 'http://grid:4444'}), patch('triage.public_browser.socket.getaddrinfo', return_value=PUBLIC), patch('triage.journey.grid_status', return_value={'ready': True}), patch('triage.journey.create_driver', return_value=driver), patch('triage.journey.verify_sandbox', return_value={}), patch('triage.journey.PublicRequests', return_value=guard), patch('triage.journey.reveal', return_value={'hit': True, 'visible': True}), patch('triage.journey.propose_step', side_effect=propose) as model:
            manager = BrowserRuns(Path(directory), Lock(), lambda: 'revision', driver_factory=controller.create_driver)
            queued = start_journey(manager, 'https://or9.ca/', [REQUEST])
            self.assertTrue(manager.generation_lock.acquire(timeout=10)); manager.generation_lock.release()
            return manager.read(queued['id']), model.call_count

    def test_native_new_tab_click_follows_guarded_destination_once(self):
        driver = NewPageDriver(); guard = Mock()
        value, calls = self.run_worker(driver, guard)
        self.assertEqual(value['status'], 'passed', value)
        self.assertEqual(calls, 1); self.assertEqual(driver.clicks, 1)
        guard.wait_for_current_target.assert_called_once_with(driver)
        action = value['steps'][-1]['actions'][0]
        self.assertEqual(action['afterUrl'], DESTINATION)
        self.assertEqual(action['navigationContext'], 'new-tab')
        self.assertEqual(value['steps'][-1]['state'], 'verified')
        self.assertEqual(driver.quits, 1); guard.close.assert_called_once()

    def test_second_page_opening_during_final_observation_prevents_success(self):
        class LateSecondPage(NewPageDriver):
            def __init__(self): super().__init__(); self.destination_observations = 0
            def execute_script(self, script, *args):
                value = super().execute_script(script, *args)
                if script == OBSERVE_PUBLIC and self.current_window_handle != 'original':
                    self.destination_observations += 1
                    if self.destination_observations == 2: self.window_handles.append('late-second')
                return value
        driver = LateSecondPage(); value, calls = self.run_worker(driver, Mock())
        self.assertEqual(value['status'], 'blocked', value)
        self.assertIn('multiple pages', value['reason']); self.assertNotIn('verifiedResult', value)
        self.assertEqual(driver.clicks, 1); self.assertEqual(calls, 1)

    def test_explicit_blank_link_waits_for_delayed_new_page_not_original_changes(self):
        class DelayedPage(NewPageDriver):
            def __init__(self):
                self.reads = 0; self.old_observations_after_click = 0; super().__init__(extra=0)
            @property
            def window_handles(self):
                if self.clicks:
                    self.reads += 1
                    if self.reads == 3: self.handles.append('delayed-new')
                return self.handles
            @window_handles.setter
            def window_handles(self, value): self.handles = value
            def execute_script(self, script, *args):
                value = super().execute_script(script, *args)
                if script == OBSERVE_PUBLIC and self.clicks and self.current_window_handle == 'original':
                    self.old_observations_after_click += 1; value['text'] = 'Original page mutated'
                return value
        driver = DelayedPage(); value, calls = self.run_worker(driver, Mock())
        self.assertEqual(value['status'], 'passed', value)
        self.assertEqual(driver.current_window_handle, 'delayed-new')
        self.assertEqual(driver.old_observations_after_click, 0)
        self.assertEqual(driver.clicks, 1); self.assertEqual(calls, 1)

    def test_guard_loss_during_destination_observation_prevents_completion(self):
        guard = Mock(); guard.disconnected = False
        class LostGuard(NewPageDriver):
            def execute_script(self, script, *args):
                value = super().execute_script(script, *args)
                if script == OBSERVE_PUBLIC and self.current_window_handle != 'original': guard.disconnected = True
                return value
        driver = LostGuard(); value, calls = self.run_worker(driver, guard)
        self.assertEqual(value['status'], 'blocked', value); self.assertNotIn('verifiedResult', value)
        self.assertEqual(driver.clicks, 1); self.assertEqual(calls, 1); self.assertEqual(driver.quits, 1)

    def test_guard_loss_during_new_page_screenshot_prevents_completion(self):
        guard = Mock(); guard.disconnected = False
        class LostGuard(NewPageDriver):
            def get_screenshot_as_png(self):
                value = super().get_screenshot_as_png()
                if self.current_window_handle != 'original': guard.disconnected = True
                return value
        driver = LostGuard(); value, calls = self.run_worker(driver, guard)
        self.assertEqual(value['status'], 'blocked', value); self.assertNotIn('verifiedResult', value)
        self.assertEqual(driver.clicks, 1); self.assertEqual(calls, 1); self.assertEqual(driver.quits, 1)

    def test_multiple_new_pages_are_not_guessed_or_reclicked(self):
        driver = NewPageDriver(extra=2); value, calls = self.run_worker(driver, Mock())
        self.assertEqual(value['status'], 'blocked', value)
        self.assertIn('multiple pages', value['reason'])
        self.assertEqual(calls, 1); self.assertEqual(driver.clicks, 1)
        self.assertNotIn('verifiedResult', value); self.assertEqual(driver.quits, 1)

    def test_failed_guard_cannot_produce_verified_completion(self):
        guard = Mock(); guard.wait_for_current_target.side_effect = ValueError('guard not ready')
        driver = NewPageDriver(); value, calls = self.run_worker(driver, guard)
        self.assertEqual(value['status'], 'failed', value)
        self.assertNotIn('verifiedResult', value)
        self.assertEqual(driver.clicks, 1); self.assertEqual(calls, 1)

    def test_internal_new_page_cannot_become_observed_success(self):
        driver = NewPageDriver(destination='http://127.0.0.1/'); value, calls = self.run_worker(driver, Mock())
        self.assertEqual(value['status'], 'failed', value)
        self.assertNotIn('verifiedResult', value)
        self.assertEqual(driver.clicks, 1); self.assertEqual(calls, 1)


if __name__ == '__main__':
    unittest.main()
