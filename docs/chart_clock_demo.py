"""Run: PYTHONPATH=.:tests python docs/chart_clock_demo.py.
Actual loopback HTTP/Selenium waits, fake DOM; invalid clock inputs are synthetic.
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

    rejections = []
    for label, clock in (('boolean', True), ('float', 100.0), ('string', '100'),
                         ('missing', None), ('nan', float('nan')), ('infinity', float('inf')),
                         ('negative', -1)):
        before_url = getattr(bot.driver, 'current_url', None)
        rejected_conversion = False
        try:
            ChartCheck.from_issue(issue, 1, sre_validated=True, now=clock)
        except GuardError:
            rejected_conversion = True
        assert rejected_conversion
        direct = check.evaluate(issue.events[-1].view, clock)
        independent = investigate_chart(issue, check, bot, now=clock)
        assert direct['state'] == independent['conclusion']['state'] == 'unknown'
        assert 'clock' in direct['uncertainty']
        assert independent['route'] is None and getattr(bot.driver, 'current_url', None) == before_url
        rejections.append({'input': label, 'conversion_rejected': True,
                           'direct': direct, 'independent': independent['conclusion'],
                           'bot_not_navigated': True})

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
    print(json.dumps({'source_base': '8587b8abdf4c15498f1d0478db771c06aa4944ec',
        'chart_checks_sha256': hashlib.sha256(Path('triage/chart_checks.py').read_bytes()).hexdigest(),
        'transport': 'actual loopback HTTP/Selenium waits; fake DOM and synthetic invalid clock inputs',
        'browser_model_video': 'NOT RUN', 'observer_actions': [e.action for e in issue.events],
        'clock_rejections': rejections, 'fresh_independent': independent,
        'same_check_release': results, 'cadence': 300, 'bounded_end': monitor.stopped,
        'observer_unchanged': True}, indent=2))
finally:
    server.shutdown()
    server.server_close()
    worker.join(2)
