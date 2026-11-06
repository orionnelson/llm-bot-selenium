"""Run: PYTHONPATH=.:tests python docs/release_expiry_demo.py.
Actual loopback HTTP/Selenium waits, fake DOM; expiry inputs are synthetic.
No real browser, model, private page, production recording or alert transport.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from threading import Thread

from test_selenium_contract import FakeHTTPDriver
from triage.mock_server import make_server
from triage.chart_browser import SeleniumChartPort
from triage.chart_checks import (ChartBinding, ChartView, SyntheticObserver, ChartCheck,
                                 investigate_chart, ReleasePlan, ReleaseMonitor)
from triage.core import Action, Context, GuardError

binding = ChartBinding(Context('synthetic', 'test', 'checkout', 50, 4000),
                       Action('overview', 'invocation_health'), 'error-rate', 'percent')
view = ChartView(binding, 'observed-first', 100, 100, 0)
server = make_server(chart=lambda route, binding: view)
worker = Thread(target=server.serve_forever, daemon=True)
worker.start()
try:
    origin = 'http://127.0.0.1:' + str(server.server_port)
    sre = SeleniumChartPort(FakeHTTPDriver(), origin)
    bot = SeleniumChartPort(FakeHTTPDriver(), origin)
    observer = SyntheticObserver(sre.session, [binding], consent=True)
    sre.read_chart('dashboard', binding)
    sre.capture(observer, 'navigate', 'dashboard', binding)
    view = replace(view, evidence_id='observed-last')
    sre.read_chart('dashboard', binding)
    sre.capture(observer, 'shortcut-open-chart', 'dashboard', binding)
    issue = observer.stop()
    check = ChartCheck.from_issue(issue, 1, sre_validated=True, now=100)
    sre_url = sre.driver.current_url

    valid = view
    view = replace(view, evidence_id='https://private.invalid/token', session_valid=False)
    independent_expired = investigate_chart(issue, check, bot, now=100)
    assert independent_expired['conclusion']['state'] == 'unknown'
    assert independent_expired['conclusion']['evidence'] is None
    expired = ReleaseMonitor(ReleasePlan(check, 100, 1600))
    expiry_result = expired.tick(100, bot)
    assert expiry_result['state'] == 'unknown' and expiry_result['evidence'] is None
    assert expired.stopped and expiry_result['report']
    bot_url = bot.driver.current_url
    view = valid
    assert expired.tick(400, bot) is None
    assert bot.driver.current_url == bot_url
    assert expired.seen_evidence == {check.source_evidence, *check.observer_evidence}

    untyped_results = []
    for state in (0, '', None, 'false'):
        monitor = ReleaseMonitor(ReleasePlan(check, 100, 1600))
        view = replace(valid, evidence_id='untyped', session_valid=state)
        rejected = monitor.tick(100, bot)
        assert rejected['state'] == 'unknown' and not monitor.stopped
        view = replace(valid, evidence_id='restored', captured_at=400, sample_at=400)
        recovery = monitor.tick(400, bot)
        assert recovery['state'] == 'healthy' and recovery['recovery']
        untyped_results.append({'input': state, 'result': rejected['state'],
                                'stopped': monitor.stopped, 'recovery': recovery['recovery']})
    view = valid
    view = replace(view, evidence_id='fresh-bot', value=8)
    independent = investigate_chart(issue, check, bot, now=100)
    assert independent['route'] == 'entity-chart' and independent['conclusion']['state'] == 'failure'
    # SAME SRE-validated check, 300-second cadence, fake caller clock, bounded end.
    monitor = ReleaseMonitor(ReleasePlan(check, 100, 1600))
    results = []
    for now, value, state in ((100, 8, 'ready'), (400, 8, 'ready'), (700, 0, 'ready'),
                               (1000, None, 'loading'), (1300, 0, 'ready')):
        view = replace(view, evidence_id='tick-' + str(now), captured_at=now,
                       sample_at=now, value=value, state=state)
        results.append({'at': now, **monitor.tick(now, bot)})
    assert [r['state'] for r in results] == ['failure', 'failure', 'healthy', 'unknown', 'healthy']
    assert [r['report'] for r in results] == [True, False, True, True, True]
    assert results[2]['recovery'] and results[4]['recovery']
    assert monitor.tick(1600, bot) is None and monitor.stopped
    assert len(issue.events) == 2 and sre.driver.current_url == sre_url
    print(json.dumps({'source_base': '2ae8cb5da3632b29b6886887346e96acf2c68f9d',
        'chart_checks_sha256': hashlib.sha256(Path('triage/chart_checks.py').read_bytes()).hexdigest(),
        'transport': 'actual loopback HTTP/Selenium waits; fake DOM and synthetic expiry inputs',
        'browser_model_video': 'NOT RUN', 'observer_actions': [e.action for e in issue.events],
        'invalid_reference_expiry': expiry_result, 'expired_plan_stopped_without_later_read': expired.stopped,
        'untyped_session_states': untyped_results, 'fresh_independent': independent,
        'same_check_release': results, 'cadence': 300, 'bounded_end': monitor.stopped,
        'observer_unchanged': True}, indent=2))
finally:
    server.shutdown()
    server.server_close()
    worker.join(2)
