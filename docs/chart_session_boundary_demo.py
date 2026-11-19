"""PYTHONPATH=.:tests python docs/chart_session_boundary_demo.py.
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
    class SwitchingPort:
        def __init__(self, port):
            self.port, self.session = port, port.session
        def read_chart(self, route, binding):
            result = self.port.read_chart(route, binding)
            self.session = sre.session
            return result
    view = replace(view, evidence_id='fresh-switched', value=8)
    switched = SwitchingPort(bot)
    rejected = investigate_chart(issue, check, switched, now=100)
    assert rejected['conclusion']['state'] == 'unknown'
    assert rejected['conclusion']['evidence'] is None
    independent = investigate_chart(issue, check, bot, now=100)
    assert independent['route'] == 'entity-chart' and independent['conclusion']['state'] == 'failure'
    assert sre.driver.current_url == sre_url and len(issue.events) == 2
    guarded_monitor = ReleaseMonitor(ReleasePlan(check, 100, 1000))
    switched = SwitchingPort(bot)
    rejected_release = guarded_monitor.tick(100, switched)
    assert rejected_release['state'] == 'unknown' and rejected_release['evidence'] is None
    assert 'fresh-switched' not in guarded_monitor.seen_evidence
    view = replace(view, evidence_id='stable-recovery', captured_at=400, sample_at=400, value=0)
    recovered = guarded_monitor.tick(400, bot)
    assert recovered['state'] == 'healthy' and recovered['recovery'] and recovered['report']
    assert guarded_monitor.tick(1000, bot) is None and guarded_monitor.stopped
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
    print(json.dumps({'source_base': '397f1d621762efcdf1755b8e5484887728de8649',
        'chart_checks_sha256': hashlib.sha256(Path('triage/chart_checks.py').read_bytes()).hexdigest(),
        'transport': 'actual loopback HTTP and Selenium waits, fake DOM; not rendered browser/model/video',
        'observer_actions': [e.action for e in issue.events],
        'session_switched_independent': rejected, 'session_switched_release': rejected_release, 'stable_release_recovery': recovered, 'fresh_independent_investigation': independent,
        'observer_unchanged': True, 'same_check_release_results': results,
        'release_cadence': monitor.plan.cadence, 'stopped_at_end': monitor.stopped}, indent=2))
finally:
    server.shutdown()
    server.server_close()
    worker.join(2)
