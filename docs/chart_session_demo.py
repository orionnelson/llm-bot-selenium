"""Executed HTTP/Selenium-wait contract; fake DOM, not rendered browser/model."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
from threading import Thread
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SOURCE), str(SOURCE / 'tests')]
from test_selenium_contract import FakeHTTPDriver, Element
from triage.mock_server import make_server
from triage.chart_browser import SeleniumChartPort
from triage.chart_checks import (ChartBinding, ChartView, SyntheticObserver, ChartCheck,
                                 investigate_chart, ReleasePlan, ReleaseMonitor)
from triage.core import Action, Context, GuardError

binding = ChartBinding(Context('synthetic', 'test', 'checkout', 0, 4000),
                       Action('overview', 'invocation_health'), 'error-rate', 'percent')
view = ChartView(binding, 'observed-first', 100, 100, 0)
server = make_server(chart=lambda route, binding: view)
worker = Thread(target=server.serve_forever, daemon=True)
worker.start()
try:
    origin = 'http://127.0.0.1:' + str(server.server_port)
    sre = SeleniumChartPort(FakeHTTPDriver(), origin)
    bot = SeleniumChartPort(FakeHTTPDriver(), origin)
    sre_session, bot_session = sre.session, bot.session
    observer = SyntheticObserver(sre.session, [binding], consent=True)
    sre.read_chart('entity-chart', binding)
    original_attribute = Element.get_attribute
    def switch_capture(element, name):
        if element.driver is sre.driver and name == 'data-chart-view':
            element.driver.session_id = 'replacement-synthetic-session'
        return original_attribute(element, name)
    with patch.object(Element, 'get_attribute', switch_capture):
        try:
            sre.capture(observer, 'navigate', 'entity-chart', binding)
        except GuardError:
            capture_rejected = True
        else:
            raise AssertionError('session-switched capture accepted')
    assert observer.events == []
    sre.driver.session_id = sre_session
    sre.capture(observer, 'navigate', 'entity-chart', binding)
    view = replace(view, evidence_id='observed-last')
    sre.read_chart('dashboard', binding)
    sre.capture(observer, 'shortcut-open-chart', 'dashboard', binding)
    issue = observer.stop()
    check = ChartCheck.from_issue(issue, 1, sre_validated=True, now=100)
    monitor = ReleaseMonitor(ReleasePlan(check, 100, 2500))
    view = replace(view, evidence_id='untrusted-session-value', value=0)
    original_load = bot.driver.get
    def switch_navigation(url):
        original_load(url)
        bot.driver.session_id = sre_session  # Fake driver only; no actual session reuse.
    with patch.object(bot.driver, 'get', switch_navigation):
        investigation = investigate_chart(issue, check, bot, now=100)
        assert investigation['conclusion']['state'] == 'unknown'
        assert investigation['conclusion']['evidence'] is None
        bot.driver.session_id = bot_session
        rejected_tick = monitor.tick(100, bot)
        assert rejected_tick['state'] == 'unknown' and rejected_tick['evidence'] is None
        assert rejected_tick['report']
        assert monitor.seen_evidence == {check.source_evidence, *check.observer_evidence}
    bot.driver.session_id = bot_session
    view = replace(view, evidence_id='independent-failure', value=8)
    independent = investigate_chart(issue, check, bot, now=100)
    assert independent['route'] == 'entity-chart' and independent['conclusion']['state'] == 'failure'
    results = []
    for now, value, state in [(400, 0, 'ready'), (700, 8, 'ready'), (1000, 8, 'ready'),
                              (1300, 0, 'ready'), (1600, None, 'loading'),
                              (1900, 0, 'ready'), (2200, 0, 'ready')]:
        view = replace(view, evidence_id='fresh-' + str(now), captured_at=now,
                       sample_at=now, value=value, state=state)
        result = monitor.tick(now, bot)
        results.append({'at': now, **result})
    assert [r['state'] for r in results] == ['healthy', 'failure', 'failure', 'healthy', 'unknown', 'healthy', 'healthy']
    assert [r['report'] for r in results] == [True, True, False, True, True, True, False]
    assert monitor.tick(2500, bot) is None and monitor.stopped
    print(json.dumps({'source_base': 'f01f3785ec0d4e8a054165abca6c43c7d8ef103d',
        'chart_browser_sha256': hashlib.sha256((SOURCE / 'triage/chart_browser.py').read_bytes()).hexdigest(),
        'transport': 'actual loopback HTTP and Selenium waits, fake DOM; no rendered browser/model/video',
        'session_changed_capture_rejected': capture_rejected, 'observer_event_count': len(issue.events),
        'observer_actions': [e.action for e in issue.events],
        'session_changed_investigation': investigation, 'session_changed_release_tick': rejected_tick,
        'rejected_tick_did_not_contaminate_evidence': True,
        'stable_independent_investigation': independent,
        'same_check_release_results': results, 'stopped_at_end': monitor.stopped}, indent=2))
finally:
    server.shutdown()
    server.server_close()
    worker.join(2)
