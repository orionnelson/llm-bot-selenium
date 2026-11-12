"""Owner Services/Contact reproduction. Not executed in the file-only session.
Run after applying the companion patch, alongside the existing journey tests.
No model inference, browser actions, submissions or email sends.
"""
import json
import unittest
from unittest.mock import patch
from triage.browser_loop import BrowserBlocked
from triage.journey import action_completed, click_matches, click_target, observe, propose_step


def control(identity, label, href='#services'):
    return {'id': identity, 'label': label, 'kind': 'control', 'tag': 'a',
            'href': href, 'expanded': None}


def page(*candidates):
    return {'url': 'https://example.com/', 'candidates': list(candidates)}


class ClickOnTargetTests(unittest.TestCase):
    def test_optional_click_preposition_and_case(self):
        for instruction, label in [('Click Services', 'Services'),
                                   ('Click on Services', 'Services'),
                                   ('Click On Contact', 'Contact'),
                                   ('Please click on Services', 'Services')]:
            with self.subTest(instruction=instruction):
                candidate = control('nav', label)
                self.assertTrue(click_matches(instruction, candidate))
                self.assertTrue(action_completed(instruction, [{'action': 'click', 'label': label}]))
                self.assertEqual(click_target(instruction, page(candidate)), [candidate])

    def test_unique_exact_services_beats_our_services(self):
        navigation = control('nav', 'Services')
        hero = control('hero', 'Our Services')
        self.assertEqual(click_target('Click on Services', page(hero, navigation)), [navigation])
        self.assertEqual(click_target('Click on Our Services', page(hero, navigation)), [hero])

    def test_duplicate_exact_labels_are_still_blocked(self):
        with self.assertRaisesRegex(BrowserBlocked, 'ambiguous'):
            click_target('Click on Services', page(control('one', 'Services'), control('two', 'Services')))

    def test_model_choices_only_include_the_exact_click_target(self):
        observation = page(control('nav', 'Services'), control('hero', 'Our Services'))
        observation['evidence'] = 'hash'
        proposal = {'python': 'def run(browser):\n    browser.click("nav", "hash")', 'result': 'Click Services'}
        with patch('triage.journey.complete', return_value=json.dumps(proposal)) as model:
            self.assertEqual(propose_step('Click on Services', observation)['candidate'], 'nav')
        choices = model.call_args.kwargs['schema']['properties']['python']['enum']
        self.assertIn(proposal['python'], choices)
        self.assertNotIn('def run(browser):\n    browser.click("hero", "hash")', choices)

    def test_absent_target_is_still_blocked(self):
        with self.assertRaisesRegex(BrowserBlocked, 'not observed'):
            click_target('Click on Services', page(control('contact', 'Contact')))

    def test_wrong_selected_control_is_still_blocked(self):
        navigation = control('nav', 'Services')
        hero = control('hero', 'Our Services')
        with self.assertRaisesRegex(BrowserBlocked, 'does not match'):
            click_target('Click on Services', page(navigation, hero), hero)

    def test_negated_target_remains_excluded(self):
        services = control('services', 'Services')
        contact = control('contact', 'Contact', '#contact')
        instruction = 'Click on Services; do not click on Contact'
        self.assertFalse(click_matches(instruction, contact))
        self.assertEqual(click_target(instruction, page(services, contact)), [services])
        self.assertFalse(click_matches('Click on Services, but not Our Services', control('hero', 'Our Services')))

    def test_literal_on_label_is_not_globally_dropped(self):
        candidate = control('on', 'On')
        self.assertEqual(click_target('Click On', page(candidate)), [candidate])
        self.assertEqual(click_target('Click on On', page(candidate)), [candidate])
        self.assertFalse(action_completed('Click On', [{'action': 'click', 'label': 'Services'}]))

    def test_mailto_does_not_send_email(self):
        email = control('email', 'Email', 'mailto:public@example.com')
        with self.assertRaisesRegex(BrowserBlocked, 'mailto'):
            click_target('Click on Email', page(email))

    def test_no_action_or_wrong_action_does_not_complete_request(self):
        self.assertFalse(action_completed('Click on Services', []))
        self.assertFalse(action_completed('Click on Services', [{'action': 'scroll', 'label': 'Services'}]))
        self.assertFalse(action_completed('Click On Contact', [{'action': 'click', 'label': 'Services'}]))

    def test_body_redaction_does_not_remove_public_control_labels(self):
        class Driver:
            def execute_script(self, script):
                return {'url': 'https://example.com/', 'documentUri': 'https://example.com/',
                        'title': 'Public fixture', 'text': 'Services token=SYNTHETIC_ONLY Contact',
                        'candidates': [control('services', 'Services')], 'facts': [], 'articles': []}
        with patch('triage.journey.public_url', return_value='https://example.com/'):
            observation = observe(Driver())
        self.assertNotIn('SYNTHETIC_ONLY', observation['text'])
        self.assertIn('[REDACTED]', observation['text'])
        self.assertEqual(click_target('Click on Services', observation)[0]['label'], 'Services')


if __name__ == '__main__':
    unittest.main()
