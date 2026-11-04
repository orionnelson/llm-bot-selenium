"""Run: PYTHONPATH=.:tests python docs/sample_order_demo.py.
Actual loopback HTTP/Selenium waits, fake DOM; sample rollback inputs are synthetic.
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
from triage.core import Action, Context

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
    observer = SyntheticObserver(sre.session, [binding], consent=True)
    sre.read_chart('dashboard', binding)
    sre.capture(observer, 'navigate', 'dashboard', binding)
    view = replace(view, evidence_id='observed-last')
    sre.read_chart('dashboard', binding)
    sre.capture(observer, 'shortcut-open-chart', 'dashboard', binding)
    issue = observer.stop()
    check = ChartCheck.from_issue(issue, 1, sre_validated=True, now=100)
    sre_url = sre.driver.current_url

    # Fresh capture IDs/times must not hide an older source sample.
    view = replace(view, evidence_id='fresh-capture-old-sample', captured_at=101, sample_at=99)
    rejected = investigate_chart(issue, check, bot, now=101)
    assert rejected['conclusion']['state'] == 'unknown'
    assert 'sample predates' in rejected['conclusion']['uncertainty']
    view = replace(view, evidence_id='same-sample', sample_at=100, value=8)
    restored = investigate_chart(issue, check, bot, now=101)
    assert restored['conclusion']['state'] == 'failure'

    # Faster bounded plans can see an otherwise-fresh sample roll backwards.
    # At cadence300 the existing <=300s freshness guard usually already rules this out.
    fast = ReleaseMonitor(ReleasePlan(check, 100, 110, cadence=1))
    rollback_results = []
    for now, sample, value in ((100, 100, 8), (101, 99, 0), (102, 100, 0), (103, 100, 0)):
        view = replace(view, evidence_id='fast-' + str(now), captured_at=now, sample_at=sample, value=value)
        rollback_results.append({'at': now, **fast.tick(now, bot)})
    assert [r['state'] for r in rollback_results] == ['failure', 'unknown', 'healthy', 'healthy']
    assert not rollback_results[1]['recovery'] and rollback_results[2]['recovery']
    assert not rollback_results[3]['report']
    assert fast.tick(110, bot) is None and fast.stopped

    view = replace(view, evidence_id='fresh-bot', captured_at=100, sample_at=100, value=8)
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
    print(json.dumps({'source_base': '5a393983ec381077c129d7c4d9b43b8ef20d59d8',
        'chart_checks_sha256': hashlib.sha256(Path('triage/chart_checks.py').read_bytes()).hexdigest(),
        'transport': 'actual loopback HTTP/Selenium waits; fake DOM and synthetic sample rollback inputs',
        'browser_model_video': 'NOT RUN', 'observer_actions': [e.action for e in issue.events],
        'independent_rollback': rejected, 'independent_restored': restored,
        'fast_release_rollback': rollback_results, 'fresh_independent': independent,
        'same_check_release': results, 'cadence': 300, 'bounded_end': monitor.stopped,
        'observer_unchanged': True}, indent=2))
finally:
    server.shutdown()
    server.server_close()
    worker.join(2)
