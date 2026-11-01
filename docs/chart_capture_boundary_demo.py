"""PYTHONPATH=.:tests python docs/chart_capture_boundary_demo.py.
Actual loopback HTTP/Selenium waits and fake DOM, not a rendered browser/model.
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
    view = replace(view, evidence_id='old-capture-new-id', captured_at=99, sample_at=99)
    rejected = investigate_chart(issue, check, bot, now=100)
    assert rejected['conclusion']['state'] == 'unknown'
    assert 'capture predates' in rejected['conclusion']['uncertainty']
    view = replace(view, evidence_id='fresh-independent', captured_at=100, sample_at=100, value=8)
    independent = investigate_chart(issue, check, bot, now=100)
    assert independent['route'] == 'entity-chart' and independent['conclusion']['state'] == 'failure'
    assert sre.driver.current_url == sre_url and len(issue.events) == 2
    # 1s caller-driven cadence exposes within-age rollback; normal 300s remains tested.
    monitor = ReleaseMonitor(ReleasePlan(check, 100, 110, cadence=1))
    results = []
    for now, captured, value, state in [(100, 99, 0, 'ready'), (101, 101, 0, 'ready'),
            (102, 102, 8, 'ready'), (103, 101, 0, 'ready'), (104, 105, 0, 'ready'),
            (105, 102, 0, 'ready'), (106, 106, 8, 'ready'), (107, 107, 8, 'ready'),
            (108, 108, None, 'loading'), (109, 109, 0, 'ready')]:
        view = replace(view, evidence_id='tick-' + str(now), captured_at=captured,
                       sample_at=min(100, captured), value=value, state=state)
        results.append({'at': now, 'captured_at': captured, **monitor.tick(now, bot)})
    assert [r['state'] for r in results] == ['unknown', 'healthy', 'failure', 'unknown',
        'unknown', 'healthy', 'failure', 'failure', 'unknown', 'healthy']
    assert [r['report'] for r in results] == [True, True, True, True, False, True, True, False, True, True]
    assert not results[3]['recovery'] and results[5]['recovery']
    assert monitor.tick(110, bot) is None and monitor.stopped
    print(json.dumps({'source_base': '866424466d4602a9a07bb3d7e7842d88aec12171',
        'chart_checks_sha256': hashlib.sha256(Path('triage/chart_checks.py').read_bytes()).hexdigest(),
        'transport': 'actual loopback HTTP and Selenium waits, fake DOM; not rendered browser/model/video',
        'observer_actions': [e.action for e in issue.events],
        'older_independent_capture': rejected, 'fresh_independent_investigation': independent,
        'observer_unchanged': True, 'same_check_release_results': results,
        'release_cadence': monitor.plan.cadence, 'stopped_at_end': monitor.stopped}, indent=2))
finally:
    server.shutdown()
    server.server_close()
    worker.join(2)
