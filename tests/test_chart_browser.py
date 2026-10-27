"""Real loopback HTTP + fake DOM, NOT rendered browser or model acceptance."""
from dataclasses import replace
import importlib.util
import threading
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from triage.chart_browser import SeleniumChartPort
from triage.chart_checks import (ChartBinding, ChartView, SyntheticObserver, ChartCheck,
                                 investigate_chart, ReleasePlan, ReleaseMonitor)
from triage.core import Action, Context, GuardError
from triage.mock_server import make_server
from test_selenium_contract import FakeHTTPDriver, Element


@unittest.skipUnless(importlib.util.find_spec('selenium'), 'Selenium package required')
class ChartDOMTests(unittest.TestCase):
    def setUp(self):
        self.now, self.value, self.changes = 100, 0, {}
        self.routes = []
        self.binding = ChartBinding(Context('synthetic', 'test', 'checkout', 0, 2000),
                                    Action('overview', 'invocation_health'),
                                    'error-rate', 'percent', (('environment', 'release'),))
        def chart(route, binding):
            self.routes.append(route)
            return replace(ChartView(binding, 'chart-' + uuid4().hex, self.now, self.now, self.value), **self.changes)
        self.server = make_server(chart=chart)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.origin = 'http://127.0.0.1:' + str(self.server.server_port)
        self.sre = SeleniumChartPort(FakeHTTPDriver(), self.origin)
        self.bot = SeleniumChartPort(FakeHTTPDriver(), self.origin)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=2)

    def issue(self):
        self.sre.read_chart('dashboard', self.binding)  # synthetic person navigates
        observer = SyntheticObserver(self.sre.session, [self.binding], consent=True)
        self.sre.capture(observer, 'navigate', 'dashboard', self.binding)
        self.sre.capture(observer, 'shortcut-open-chart', 'dashboard', self.binding)
        issue = observer.stop()
        check = ChartCheck.from_issue(issue, 1, sre_validated=True, now=self.now)
        return issue, check

    def test_http_dom_observation_independent_navigation_and_release_reuse(self):
        issue, check = self.issue()
        original_url = self.sre.driver.current_url
        self.value = 8
        result = investigate_chart(issue, check, self.bot, now=self.now)
        self.assertEqual(result['conclusion']['state'], 'failure')
        self.assertEqual(result['route'], 'entity-chart')
        self.assertEqual(self.sre.driver.current_url, original_url)
        self.assertEqual(self.routes, ['dashboard', 'entity-chart'])
        self.assertNotIn('Ignore', str(issue))
        session = self.sre.export_studio_session(issue, consent=True)
        self.assertEqual([e['action'] for e in session['events']], ['navigate', 'shortcut-open-chart'])
        self.assertNotIn('binding', str(session))
        self.assertEqual(self.sre.driver.current_url, original_url)
        monitor = ReleaseMonitor(ReleasePlan(check, 100, 1000))
        self.assertTrue(monitor.tick(100, self.bot)['report'])
        self.now = 400
        self.assertFalse(monitor.tick(400, self.bot)['report'])
        self.value, self.now = 0, 700
        self.assertEqual(monitor.tick(700, self.bot)['state'], 'healthy')
        reads = len(self.routes)
        self.assertIsNone(monitor.tick(1000, self.bot))
        self.assertEqual(len(self.routes), reads)

    def test_duplicate_json_evidence_is_rejected_before_observation_and_recovers(self):
        issue, check = self.issue()
        original_get = Element.get_attribute
        # Every conflicting pair used to keep the final (apparently healthy) value.
        pairs = [('"session_valid": true', '"session_valid": false, "session_valid": true'),
                 ('"sample_at": 100', '"sample_at": -400, "sample_at": 100'),
                 ('"chart": "error-rate"', '"chart": "other", "chart": "error-rate"'),
                 ('"function": "checkout"', '"function": "other", "function": "checkout"')]
        for old, ambiguous in pairs:
            with self.subTest(field=old):
                def get_attribute(element, name):
                    value = original_get(element, name)
                    if name == 'data-chart-view':
                        self.assertIn(old, value)
                        return value.replace(old, ambiguous, 1)
                    return value
                monitor = ReleaseMonitor(ReleasePlan(check, 100, 1000))
                observer = SyntheticObserver(self.sre.session, [self.binding], consent=True)
                with patch.object(Element, 'get_attribute', get_attribute):
                    with self.assertRaises(GuardError):
                        self.sre.capture(observer, 'navigate', 'dashboard', self.binding)
                    self.assertEqual(observer.events, [])
                    result = investigate_chart(issue, check, self.bot, now=100)
                    self.assertEqual(result['conclusion']['state'], 'unknown')
                    self.assertIsNone(result['conclusion']['evidence'])
                    result = monitor.tick(100, self.bot)
                    self.assertEqual(result['state'], 'unknown')
                    self.assertTrue(result['report'])
                    self.assertIsNone(result['evidence'])
                    self.assertEqual(monitor.seen_evidence, {check.source_evidence})
                self.now = 400
                result = monitor.tick(400, self.bot)
                self.assertEqual(result['state'], 'healthy')
                self.assertFalse(result['report'])
                self.now = 100

    def test_http_dom_sample_newer_than_capture_is_not_trusted(self):
        issue, check = self.issue()
        self.changes = {'captured_at': 99}  # Sample=100 and now=100: fresh but inconsistent.
        result = investigate_chart(issue, check, self.bot, now=self.now)
        self.assertEqual(result['conclusion']['state'], 'unknown')
        monitor = ReleaseMonitor(ReleasePlan(check, 100, 1000))
        result = monitor.tick(100, self.bot)
        self.assertEqual(result['state'], 'unknown')
        self.assertTrue(result['report'])
        with self.assertRaises(GuardError):
            self.issue()
        self.changes, self.now = {}, 400
        result = monitor.tick(400, self.bot)
        self.assertEqual(result['state'], 'healthy')
        self.assertFalse(result['report'])

    def test_http_dom_replayed_earlier_observer_evidence_is_unknown(self):
        self.sre.read_chart('entity-chart', self.binding)
        observer = SyntheticObserver(self.sre.session, [self.binding], consent=True)
        self.sre.capture(observer, 'navigate', 'entity-chart', self.binding)
        earlier = observer.events[-1].view.evidence_id
        self.sre.read_chart('dashboard', self.binding)
        self.sre.capture(observer, 'shortcut-open-chart', 'dashboard', self.binding)
        issue = observer.stop()
        check = ChartCheck.from_issue(issue, 1, sre_validated=True, now=100)
        self.assertNotEqual(earlier, check.source_evidence)
        original_url = self.sre.driver.current_url
        self.changes = {'evidence_id': earlier}
        for value in (0, 8):
            with self.subTest(value=value):
                self.value = value
                result = investigate_chart(issue, check, self.bot, now=100)
                self.assertEqual(result['conclusion']['state'], 'unknown')
                self.assertEqual(result['conclusion']['evidence'], earlier)
                self.assertEqual(self.sre.driver.current_url, original_url)
                monitor = ReleaseMonitor(ReleasePlan(check, 100, 1000))
                release = monitor.tick(100, self.bot)
                self.assertEqual(release['state'], 'unknown')
                self.assertEqual(release['evidence'], earlier)
                self.assertTrue(release['report'])
                self.assertEqual(monitor.seen_evidence, {earlier, check.source_evidence})
        self.changes = {}
        self.assertEqual(investigate_chart(issue, check, self.bot, now=100)['conclusion']['state'], 'failure')
        monitor = ReleaseMonitor(ReleasePlan(check, 100, 1000))
        self.assertEqual(monitor.tick(100, self.bot)['state'], 'failure')
        self.assertTrue(monitor.tick(400, self.bot)['duplicate'])
        self.value, self.now = 0, 700
        self.assertEqual(monitor.tick(700, self.bot)['state'], 'healthy')
        reads = len(self.routes)
        self.assertIsNone(monitor.tick(1000, self.bot))
        self.assertEqual(len(self.routes), reads)

    def test_dom_loading_missing_stale_drift_session_and_changed_filters(self):
        issue, check = self.issue()
        for changes in ({'state': 'loading'}, {'value': None}, {'sample_at': -400},
                        {'ui_version': 'chart-v2'}, {'session_valid': False},
                        {'binding': replace(self.binding, filters=())},
                        {'binding': replace(self.binding, context=replace(self.binding.context, start=1))}):
            with self.subTest(changes=changes):
                self.changes = changes
                result = investigate_chart(issue, check, self.bot, now=self.now)
                self.assertEqual(result['conclusion']['state'], 'unknown')
                monitor = ReleaseMonitor(ReleasePlan(check, 100, 1000))
                self.assertEqual(monitor.tick(100, self.bot)['state'], 'unknown')
                self.assertEqual(monitor.stopped, changes.get('session_valid') is False)

    def test_guards_before_dom_access_and_navigation(self):
        driver = Mock(session_id='same-driver')
        port = SeleniumChartPort(driver, self.origin)
        observer = SyntheticObserver('same-driver', [self.binding], consent=True)
        for action, route, binding in [('keypress', 'dashboard', self.binding),
                                       ('navigate', 'https://evil', self.binding),
                                       ('navigate', 'dashboard', replace(self.binding, chart='other'))]:
            with self.subTest(action=action, route=route), self.assertRaises(GuardError):
                port.capture(observer, action, route, binding)
        observer.stop()
        with self.assertRaises(GuardError):
            port.capture(observer, 'navigate', 'dashboard', self.binding)
        driver.get.assert_not_called()
        driver.find_element.assert_not_called()
        with self.assertRaises(GuardError):
            port.read_chart('delete', self.binding)
        driver.get.assert_not_called()

    def test_session_identity_cannot_be_aliased_and_origin_hidden_payload_fail_closed(self):
        issue, check = self.issue()
        alias = SeleniumChartPort(self.sre.driver, self.origin)
        with self.assertRaises(GuardError):
            investigate_chart(issue, check, alias, now=100)
        self.sre.driver.current_url = 'https://example.com/chart/dashboard'
        with self.assertRaises(GuardError):
            self.sre.read_visible(self.binding, 'dashboard')
        self.sre.read_chart('dashboard', self.binding)
        element = self.sre.driver.find_element(None, '[data-chart-view]')
        element.is_displayed = lambda: False
        with self.assertRaises(GuardError):
            self.sre.read_visible(self.binding, 'dashboard')
        element.is_displayed = lambda: True
        for text, payload in [('true', '{'), ('0', '[]'), ('0', 'null'),
                              ('0', 'x' * 8193), ('0' * 81, '{}')]:
            element.text, element.attrs['data-chart-view'] = text, payload
            with self.assertRaises(GuardError):
                self.sre.read_visible(self.binding, 'dashboard')

    def test_same_origin_navigation_during_read_is_rejected(self):
        for stage in ('wait', 'payload', 'text'):
            for target in ('/chart/entity-chart', '/login', '/chart/dashboard?changed=filters'):
                with self.subTest(stage=stage, target=target):
                    self.sre.read_chart('dashboard', self.binding)
                    element = self.sre.driver.find_element(None, '[data-chart-view]')
                    payload, text = element.get_attribute('data-chart-view'), element.text
                    port = self.sre
                    reads = []

                    class NavigatingElement:
                        def is_displayed(self):
                            return True

                        def get_attribute(self, name):
                            reads.append('payload')
                            if stage == 'payload':
                                port.driver.current_url = self.origin + target
                            return payload

                        @property
                        def text(self):
                            reads.append('text')
                            if stage == 'text':
                                port.driver.current_url = self.origin + target
                            return text

                    wrapped = NavigatingElement()
                    wrapped.origin = self.origin
                    def wait(selector):
                        if stage == 'wait':
                            port.driver.current_url = self.origin + target
                        return wrapped
                    original_wait = port._wait
                    port._wait = wait
                    observer = SyntheticObserver(port.session, [self.binding], consent=True)
                    try:
                        with self.assertRaises(GuardError):
                            port.capture(observer, 'navigate', 'dashboard', self.binding)
                        self.assertEqual(observer.events, [])
                        if stage == 'wait':
                            self.assertEqual(reads, [])
                    finally:
                        port._wait = original_wait

    def test_navigation_during_bot_read_is_unknown_then_recovers_for_release(self):
        issue, check = self.issue()
        original_wait = self.bot._wait
        def redirect(selector):
            element = original_wait(selector)
            self.bot.driver.current_url = self.origin + '/login'
            return element
        self.bot._wait = redirect
        monitor = ReleaseMonitor(ReleasePlan(check, 100, 1000))
        try:
            self.assertEqual(investigate_chart(issue, check, self.bot, now=100)['conclusion']['state'], 'unknown')
            result = monitor.tick(100, self.bot)
            self.assertEqual(result['state'], 'unknown')
            self.assertTrue(result['report'])
            self.assertEqual(monitor.seen_evidence, {check.source_evidence})
        finally:
            self.bot._wait = original_wait
        self.now = 400
        self.assertEqual(monitor.tick(400, self.bot)['state'], 'healthy')
        self.assertEqual(investigate_chart(issue, check, self.bot, now=400)['conclusion']['state'], 'healthy')

    def test_redirect_during_wait_is_rejected_before_reading_payload(self):
        self.sre.read_chart('dashboard', self.binding)
        element = Mock()
        def redirect(selector):
            self.sre.driver.current_url = 'https://example.com/chart/dashboard'
            return element
        self.sre._wait = redirect
        with self.assertRaises(GuardError):
            self.sre.read_visible(self.binding, 'dashboard')
        element.get_attribute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
