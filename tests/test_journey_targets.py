"""The named target is checked before dispatch, not after a wrong click."""
import json
import unittest
from unittest.mock import patch

from triage.browser_loop import BrowserBlocked
from triage.journey import action_completed, propose_step, OBSERVE_PUBLIC, CODER
from test_journey import Driver
from journey_guard_helpers import JourneyRecoveryTests

REQUEST = 'Click the Email Button Sideways on The Right of the Screen do Not Click Allenfort'


def observation(href='mailto:test@example.com'):
    return {'url': 'https://or9.ca/', 'documentUri': 'https://or9.ca/', 'title': 'Synthetic contact page',
            'text': 'Allenfort Email News', 'facts': [], 'articles': [], 'evidence': 'a' * 64,
            'candidates': [{'id': 'c20', 'label': 'Allenfort', 'kind': 'control', 'href': '/wrong'},
                           {'id': 'c22', 'label': 'Email', 'kind': 'control', 'href': href},
                           {'id': 'c23', 'label': 'News', 'kind': 'control', 'href': '/news'}]}


class ContactDriver(Driver):
    def __init__(self, href='mailto:test@example.com'):
        super().__init__()
        self.href = href
        self.dispatched = []

    def execute_script(self, script, *args):
        if script == OBSERVE_PUBLIC:
            result = observation(self.href)
            result.update(url=self.current_url, documentUri=self.current_url)
            if self.clicked: result['text'] += ' Email opened'
            return result
        return None

    def find_element(self, by, selector):
        driver = self
        class Target:
            def is_displayed(self): return True
            def is_enabled(self): return True
            def click(self):
                driver.dispatched.append(selector)
                driver.clicked = True
                driver.current_url = "https://or9.ca" + driver.href if driver.href.startswith("/") else driver.current_url
        return Target()


class RequestedTargetTests(unittest.TestCase):
    def test_reported_email_request_recognizes_positive_target_not_exclusion_or_position(self):
        self.assertTrue(action_completed(REQUEST, [{'action': 'click', 'label': 'Email'}]))
        self.assertFalse(action_completed(REQUEST, [{'action': 'click', 'label': 'Allenfort'}]))

    def test_mailto_is_explicitly_blocked_before_any_model_call(self):
        with patch('triage.journey.complete') as model:
            with self.assertRaisesRegex(BrowserBlocked, 'external mail client'):
                propose_step(REQUEST, observation())
            model.assert_not_called()

    def test_wrong_http_target_never_enters_click_source_enum(self):
        def complete(messages, **kwargs):
            sources = kwargs['schema']['properties']['python']['enum']
            self.assertFalse(any('browser.click("c20"' in source for source in sources))
            self.assertFalse(any('browser.click("c23"' in source for source in sources))
            self.assertTrue(any('browser.click("c22"' in source for source in sources))
            return json.dumps({'python': 'def run(browser):\n    browser.click("c22", "' + 'a' * 64 + '")', 'result': 'Email'})
        with patch('triage.journey.complete', side_effect=complete):
            self.assertEqual(propose_step(REQUEST, observation('/contact'))['candidate'], 'c22')

    def test_unobserved_named_target_is_not_replaced_by_another_control(self):
        with patch('triage.journey.complete') as model:
            with self.assertRaisesRegex(BrowserBlocked, 'not observed'):
                propose_step('Click Support', observation())
            model.assert_not_called()

    def test_ambiguous_named_target_is_not_guessed(self):
        obs = observation('/contact')
        obs['candidates'].append({'id': 'c24', 'label': 'Email', 'kind': 'control', 'href': '/other-contact'})
        with patch('triage.journey.complete') as model:
            with self.assertRaisesRegex(BrowserBlocked, 'ambiguous'):
                propose_step('Click Email', obs)
            model.assert_not_called()

    def test_worker_blocks_wrong_target_even_if_planner_validation_is_bypassed(self):
        value, _, driver = JourneyRecoveryTests().run_worker([REQUEST], lambda _, obs: {'action': 'click', 'candidate': 'c20', 'evidence': obs['evidence']}, ContactDriver('/contact'))
        self.assertEqual(value['status'], 'blocked', value)
        self.assertEqual(driver.dispatched, [])
        self.assertEqual(value['steps'][-1]['actions'], [])
        self.assertNotIn('verifiedResult', value)
        self.assertEqual(driver.quits, 1)

    def test_worker_blocks_mailto_without_dispatch_or_success_claim(self):
        value, _, driver = JourneyRecoveryTests().run_worker([REQUEST], lambda _, obs: {'action': 'click', 'candidate': 'c22', 'evidence': obs['evidence']}, ContactDriver())
        self.assertEqual(value['status'], 'blocked', value)
        self.assertIn('external mail client', value['steps'][-1]['failureReason'])
        self.assertEqual(driver.dispatched, [])
        self.assertEqual(value['steps'][-1]['actions'], [])
        self.assertNotIn('verifiedResult', value)

    def test_matching_web_email_control_still_clicks_and_completes(self):
        value, count, driver = JourneyRecoveryTests().run_worker([REQUEST], lambda _, obs: {'action': 'click', 'candidate': 'c22', 'evidence': obs['evidence']}, ContactDriver('/contact'))
        self.assertEqual(value['status'], 'passed', value)
        self.assertEqual(count, 1)
        self.assertEqual(driver.dispatched, ['[data-journey-candidate="c22"]'])
        self.assertEqual(value['steps'][-1]['actions'][0]['label'], 'Email')

    def test_explicit_negative_target_blocks_click_even_for_non_click_instruction(self):
        value, _, driver = JourneyRecoveryTests().run_worker(['Inspect contacts but do not click Allenfort'], lambda _, obs: {'action': 'click', 'candidate': 'c20', 'evidence': obs['evidence']}, ContactDriver('/contact'))
        self.assertEqual(value['status'], 'blocked', value)
        self.assertEqual(driver.dispatched, [])

    def test_on_in_a_control_name_is_not_treated_as_a_position(self):
        self.assertTrue(action_completed('Click Power on', [{'action': 'click', 'label': 'Power on'}]))
        self.assertFalse(action_completed('Click Power on', [{'action': 'click', 'label': 'Power off'}]))

    def test_requested_model_is_qwen36_q4_no_thinking(self):
        self.assertEqual(CODER, 'Qwen3.6-35B-A3B-UD-Q4_K_M-no-think')
