"""Semantic metadata export only: no browser, video or model acceptance."""
from dataclasses import replace
import unittest
from unittest.mock import Mock

from triage.chart_browser import SeleniumChartPort
from triage.chart_checks import ChartBinding, ChartView, IssueBundle, SyntheticObserver
from triage.core import Action, Context, GuardError


class StudioSessionTests(unittest.TestCase):
    def setUp(self):
        self.driver = Mock(session_id='observer-driver')
        self.port = SeleniumChartPort(self.driver, 'http://127.0.0.1:8765')
        self.binding = ChartBinding(Context('synthetic', 'test', 'checkout', 0, 2000),
                                    Action('overview', 'invocation_health'), 'errors', 'percent')
        self.view = ChartView(self.binding, 'evidence-1', 100, 100, 0)
        observer = SyntheticObserver(self.port.session, [self.binding], consent=True)
        observer.record('navigate', 'dashboard', self.view)
        observer.record('shortcut-open-chart', 'entity-chart', replace(self.view, captured_at=102))
        self.issue = observer.stop()
        self.driver.reset_mock()

    def test_exports_allowlisted_metadata_relative_time_and_semantic_shortcut(self):
        result = self.port.export_studio_session(self.issue, consent=True)
        self.assertEqual(result['version'], 'triage-session/v1')
        self.assertEqual(result['provenance'], 'imported')
        self.assertEqual(result['mode'], 'recorded')
        self.assertEqual(result['url'], 'http://127.0.0.1:8765/chart/dashboard')
        self.assertEqual([e['elapsedMs'] for e in result['events']], [0, 2000])
        self.assertEqual([e['action'] for e in result['events']], ['navigate', 'shortcut-open-chart'])
        self.assertEqual(len({e['id'] for e in result['events']}), 2)
        self.assertEqual(set(result['events'][0]), {'id', 'elapsedMs', 'action', 'url'})
        self.assertNotIn('checkout', str(result))
        self.assertNotIn('evidence-1', str(result))
        self.assertNotIn(self.driver.session_id, str(result))
        self.assertEqual(self.driver.mock_calls, [])
        self.assertEqual(self.issue.events[-1].view.captured_at, 102)

    def test_requires_explicit_export_consent_matching_session_and_nonempty_issue(self):
        for issue, consent in [(self.issue, False), (self.issue, 1),
                               (replace(self.issue, observer_session='bot-driver'), True),
                               (IssueBundle(self.port.session, ()), True)]:
            with self.subTest(issue=issue, consent=consent), self.assertRaises(GuardError):
                self.port.export_studio_session(issue, consent=consent)
        self.assertEqual(self.driver.mock_calls, [])

    def test_revalidates_forged_event_routes_actions_timestamps_and_budget(self):
        first, last = self.issue.events
        for event in [replace(last, route='https://private.example/?token=secret'),
                      replace(last, action='keypress'),
                      replace(last, view=replace(last.view, captured_at=99)),
                      replace(last, view=replace(last.view, captured_at=True)),
                      replace(last, view=replace(last.view, captured_at=86501))]:
            with self.subTest(event=event), self.assertRaises(GuardError):
                self.port.export_studio_session(replace(self.issue, events=(first, event)), consent=True)
        with self.assertRaises(GuardError):
            self.port.export_studio_session(replace(self.issue, events=(first,) * 101), consent=True)
        self.assertEqual(self.driver.mock_calls, [])

    def test_unknown_loading_and_expired_evidence_is_not_upgraded_to_healthy(self):
        event = replace(self.issue.events[0], view=replace(self.view, state='loading', session_valid=False, value=None))
        result = self.port.export_studio_session(replace(self.issue, events=(event,)), consent=True)
        self.assertNotIn('healthy', str(result))
        self.assertNotIn('success', str(result))
        self.assertEqual(result['events'][0]['action'], 'navigate')


if __name__ == '__main__':
    unittest.main()
