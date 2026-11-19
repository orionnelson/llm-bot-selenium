"""Run from repository root: PYTHONPATH=.:tests python docs/chart_provenance_demo.py.
Actual loopback HTTP/Selenium waits, fake DOM; no rendered browser or model.
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
view = ChartView(binding, 'observed-first', 100, 100, 8)
server = make_server(chart=lambda route, binding: view)
worker = Thread(target=server.serve_forever, daemon=True)
worker.start()
try:
    origin = 'http://127.0.0.1:' + str(server.server_port)
    sre = SeleniumChartPort(FakeHTTPDriver(), origin)
    bot = SeleniumChartPort(FakeHTTPDriver(), origin)
    observer = SyntheticObserver(sre.session, [binding], consent=True)
    sre.read_chart('entity-chart', binding)
    sre.capture(observer, 'navigate', 'entity-chart', binding)
    view = replace(view, evidence_id='observed-last', value=0)
    sre.read_chart('dashboard', binding)
    sre.capture(observer, 'shortcut-open-chart', 'dashboard', binding)
    issue = observer.stop()
    check = ChartCheck.from_issue(issue, 1, sre_validated=True, now=100)
    compact_issue = replace(issue, events=issue.events[-1:])
    sre_url = sre.driver.current_url
    view = replace(view, evidence_id='observed-first')
    rejected = investigate_chart(compact_issue, check, bot, now=100)
    assert rejected['conclusion']['state'] == 'unknown'
    assert rejected['conclusion']['uncertainty'] == 'reused observer evidence'
    monitor = ReleaseMonitor(ReleasePlan(check, 100, 2500))
    release_rejected = monitor.tick(100, bot)
    assert release_rejected['state'] == 'unknown' and release_rejected['report']
    assert monitor.seen_evidence == {'observed-first', 'observed-last'}
    view = replace(view, evidence_id='independent-bot', value=8)
    independent = investigate_chart(compact_issue, check, bot, now=100)
    assert independent['route'] == 'entity-chart' and independent['conclusion']['state'] == 'failure'
    assert sre.driver.current_url == sre_url and len(issue.events) == 2
    results = []
    for now, value, state in [(400, 0, 'ready'), (700, 8, 'ready'), (1000, 8, 'ready'),
                              (1300, 0, 'ready'), (1600, None, 'loading'),
                              (1900, 0, 'ready'), (2200, 0, 'ready')]:
        view = replace(view, evidence_id='fresh-' + str(now), captured_at=now,
                       sample_at=now, value=value, state=state)
        results.append({'at': now, **monitor.tick(now, bot)})
    assert [r['state'] for r in results] == ['healthy', 'failure', 'failure', 'healthy', 'unknown', 'healthy', 'healthy']
    assert [r['report'] for r in results] == [True, True, False, True, True, True, False]
    assert monitor.tick(2500, bot) is None and monitor.stopped
    print(json.dumps({'source_base': '0dbe62b9a973f5fae084cdfc73a4b36116081905',
        'chart_checks_sha256': hashlib.sha256(Path('triage/chart_checks.py').read_bytes()).hexdigest(),
        'transport': 'actual loopback HTTP and Selenium waits, fake DOM; no rendered browser/model/video',
        'observer_actions': [e.action for e in issue.events],
        'original_issue_events': len(issue.events), 'supplied_issue_events': len(compact_issue.events),
        'retained_check_provenance': check.observer_evidence,
        'truncated_issue_investigation': rejected, 'same_check_replayed_release': release_rejected,
        'fresh_independent_investigation': independent, 'observer_unchanged': True,
        'same_check_release_results': results, 'stopped_at_end': monitor.stopped}, indent=2))
finally:
    server.shutdown()
    server.server_close()
    worker.join(2)
