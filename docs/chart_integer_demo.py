"""Run: PYTHONPATH=.:tests python docs/chart_integer_demo.py.
Actual loopback HTTP/Selenium waits, fake DOM; integer inputs are synthetic.
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

    huge = 10 ** 400
    integer_check = ChartCheck.from_issue(issue, huge, sre_validated=True, now=100)
    view = replace(view, evidence_id='http-bot', value=8)
    http_result = investigate_chart(issue, integer_check, bot, now=100)
    assert http_result['conclusion']['state'] == 'healthy'
    assert http_result['conclusion']['maximum'] == huge
    integer_monitor = ReleaseMonitor(ReleasePlan(integer_check, 100, 1000))
    assert integer_monitor.tick(100, bot)['state'] == 'healthy'
    # Unchanged browser-adapter budget still refuses oversized DOM numeric text.
    view = replace(view, evidence_id='oversized-dom', value=huge, captured_at=400, sample_at=400)
    budget_rejection = integer_monitor.tick(400, bot)
    assert budget_rejection['state'] == 'unknown'
    view = replace(view, evidence_id='http-restored', value=0, captured_at=700, sample_at=700)
    restored = integer_monitor.tick(700, bot)
    assert restored['recovery']
    assert integer_monitor.tick(1000, bot) is None and integer_monitor.stopped

    # Pure Python adapter exercises exact integers, not a bypass of DOM budgets.
    class IntegerAdapter:
        session = 'synthetic-integer-bot'
        def read_chart(self, route, binding):
            return self.view
    exact = IntegerAdapter()
    exact.view = replace(issue.events[-1].view, evidence_id='exact-int', value=huge + 1)
    exact_failure = investigate_chart(issue, integer_check, exact, now=100)
    assert exact_failure['conclusion']['state'] == 'failure'
    exact_monitor = ReleaseMonitor(ReleasePlan(integer_check, 100, 1000))
    assert exact_monitor.tick(100, exact)['state'] == 'failure'
    exact.view = replace(exact.view, evidence_id='exact-equality', captured_at=400, sample_at=400, value=huge)
    exact_recovery = exact_monitor.tick(400, exact)
    assert exact_recovery['recovery']
    assert exact_monitor.tick(1000, exact) is None and exact_monitor.stopped

    view = replace(issue.events[-1].view, evidence_id='fresh-bot', value=8)
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
    print(json.dumps({'source_base': '6ca4fd110335568ada5922d8ca002b3f0c40a110',
        'chart_checks_sha256': hashlib.sha256(Path('triage/chart_checks.py').read_bytes()).hexdigest(),
        'transport': 'actual loopback HTTP/Selenium waits, fake DOM; separate pure Python integer adapter',
        'browser_model_video': 'NOT RUN', 'observer_actions': [e.action for e in issue.events],
        'explicit_integer_threshold_digits': len(str(huge)),
        'http_threshold_result': http_result['conclusion']['state'],
        'oversized_dom_still_unknown': budget_rejection['state'], 'http_recovery': restored['recovery'],
        'exact_integer_above_threshold': exact_failure['conclusion']['state'],
        'exact_integer_equality_recovery': exact_recovery['recovery'],
        'fresh_independent': independent, 'same_check_release': results,
        'cadence': 300, 'bounded_end': monitor.stopped, 'observer_unchanged': True}, indent=2))

finally:
    server.shutdown()
    server.server_close()
    worker.join(2)
