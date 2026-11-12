"""Verified actions advance once; directional prose is not a target name."""
import unittest
from unittest.mock import patch
from selenium.common.exceptions import TimeoutException

from triage.browser_loop import BrowserBlocked
from triage.journey import action_completed, reveal, simple_action_goal
import journey_guard_helpers as recovery
from test_journey import Driver


class ActionCompletionTests(unittest.TestCase):
    def test_scroll_direction_and_pacing_are_not_target_names(self):
        for request in ['Scroll Dow To Projects', 'Scroll down to Projects', 'Scroll to the Projects section', 'Scroll slowly down to Projects', 'Scroll down a little to Projects', 'Find the Projects section']:
            with self.subTest(request=request):
                self.assertTrue(action_completed(request, [{'action': 'scroll', 'label': 'Projects'}]))
                self.assertFalse(action_completed(request, [{'action': 'scroll', 'label': 'Employers'}]))
                self.assertFalse(action_completed(request, [{'action': 'click', 'label': 'Projects'}]))

    def test_direction_normalization_does_not_change_a_click_target(self):
        self.assertTrue(action_completed('Click Dow', [{'action': 'click', 'label': 'Dow'}]))
        self.assertFalse(action_completed('Click Dow', [{'action': 'click', 'label': 'Projects'}]))

    def test_reported_scroll_advances_without_another_planning_call(self):
        value, count, driver = recovery.JourneyRecoveryTests().run_worker(['Scroll Dow To Projects'], lambda _, obs: {'action': 'scroll', 'candidate': 'c0', 'evidence': obs['evidence']})
        self.assertEqual(value['status'], 'passed', value)
        self.assertEqual(count, 1)
        self.assertEqual(value['steps'][-1]['state'], 'verified')
        self.assertEqual(len(value['steps'][-1]['actions']), 1)
        self.assertEqual(value['steps'][-1]['actions'][0]['label'], 'Projects')
        self.assertEqual(driver.quits, 1)

    def test_next_instruction_runs_instead_of_repeating_successful_scroll(self):
        calls = []
        def propose(instruction, obs):
            calls.append(instruction)
            if instruction.lower().startswith('scroll'): return {'action': 'scroll', 'candidate': 'c0', 'evidence': obs['evidence']}
            return recovery.JourneyRecoveryTests.finish(instruction, obs)
        value, count, _ = recovery.JourneyRecoveryTests().run_worker(['Scroll Dow To Projects', 'Screenshot the page'], propose)
        self.assertEqual(value['status'], 'passed', value)
        self.assertEqual(calls, ['Scroll Dow To Projects', 'Screenshot the page'])
        self.assertEqual(count, 2)
        self.assertTrue(all(step['state'] == 'verified' for step in value['steps']))

    def test_compound_scroll_still_requires_the_requested_inspection(self):
        self.assertFalse(simple_action_goal('Scroll down to Projects and inspect the cards'))
        self.assertFalse(simple_action_goal('Click News to read the articles'))
        self.assertTrue(simple_action_goal('Scroll Dow To Projects'))

    def test_already_visible_target_requires_stability_and_hit_test(self):
        class Browser:
            calls = 0
            def execute_script(self, script, *args):
                self.calls += 1
                if 'scrollIntoView' in script: return None
                return {'x': 10, 'y': 50, 'visible': True, 'hit': True}
        browser = Browser()
        class Wait:
            def __init__(self, *args, **kwargs): pass
            def until(self, condition):
                self.assertFalse(condition(browser))
                result = condition(browser)
                self.assertTrue(result)
                return result
        Wait.assertFalse = self.assertFalse
        Wait.assertTrue = self.assertTrue
        with patch('selenium.webdriver.support.ui.WebDriverWait', Wait):
            evidence = reveal(browser, object())
        self.assertEqual(evidence, {'x': 10, 'y': 50, 'visible': True, 'hit': True})
        self.assertEqual(browser.calls, 3)

    def test_covered_target_is_not_verified(self):
        class Browser:
            def execute_script(self, script, *args):
                return None if 'scrollIntoView' in script else {'x': 10, 'y': 50, 'visible': True, 'hit': False}
        browser = Browser()
        class Wait:
            def __init__(self, *args, **kwargs): pass
            def until(self, condition):
                self.assertFalse(condition(browser))
                self.assertFalse(condition(browser))
                raise TimeoutException('Covered target')
        Wait.assertFalse = self.assertFalse
        with patch('selenium.webdriver.support.ui.WebDriverWait', Wait), self.assertRaises(BrowserBlocked):
            reveal(browser, object())

    def test_successful_click_still_advances_once(self):
        value, count, driver = recovery.JourneyRecoveryTests().run_worker(['Click Security News'], lambda _, obs: {'action': 'click', 'candidate': 'c1', 'evidence': obs['evidence']})
        self.assertEqual(value['status'], 'passed', value)
        self.assertEqual(count, 1)
        self.assertTrue(driver.clicked)
        self.assertEqual(len(value['steps'][-1]['actions']), 1)

    def test_unrelated_text_change_cannot_verify_click(self):
        class AnimationDriver(Driver):
            def execute_script(self, script, *args):
                value = super().execute_script(script, *args)
                if isinstance(value, dict) and 'candidates' in value:
                    for candidate in value['candidates']:
                        if candidate['id'] == 'c1': candidate['expanded'] = 'false'
                return value
        with patch('selenium.webdriver.support.ui.WebDriverWait') as wait:
            from selenium.common.exceptions import TimeoutException
            wait.return_value.until.side_effect = TimeoutException('No destination/control state change')
            value, count, driver = recovery.JourneyRecoveryTests().run_worker(['Click News'], lambda _, obs: {'action': 'click', 'candidate': 'c1', 'evidence': obs['evidence']}, AnimationDriver())
        self.assertEqual(value['status'], 'blocked')
        self.assertEqual(count, 1)
        self.assertEqual(driver.quits, 1)
        self.assertNotIn('verifiedResult', value)

    def test_cancellation_during_reveal_is_not_relabelled_as_success(self):
        class Browser:
            def execute_script(self, *args): return None
        def cancelled(): raise InterruptedError('Cancelled')
        with self.assertRaises(InterruptedError): reveal(Browser(), object(), cancelled)


    def test_duplicate_or_private_dispatch_target_is_rejected(self):
        from triage.journey import resolve_target
        class Browser:
            def __init__(self, count, metadata): self.count, self.metadata = count, metadata
            def find_elements(self, *args): return [object()] * self.count
            def execute_script(self, *args): return self.metadata
        candidate = {'id':'c0','label':'News','href':'/news','kind':'control','tag':'a'}
        for browser in [Browser(2, candidate), Browser(1, None), Browser(1, dict(candidate, tag='button'))]:
            with self.subTest(browser=browser), self.assertRaises(BrowserBlocked): resolve_target(browser, candidate)
        self.assertIsNotNone(resolve_target(Browser(1, candidate), candidate))
