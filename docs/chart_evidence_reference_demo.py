"""Run: PYTHONPATH=.:tests python docs/chart_evidence_reference_demo.py.
Actual loopback HTTP/Selenium waits, fake DOM; malformed adapter injection is synthetic.
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

    class MalformedReferencePort:
        session = bot.session
        def read_chart(self, route, binding):
            # Injection at custom-adapter boundary, NOT a claim that Selenium parser accepts this.
            return replace(bot.read_chart(route, binding), evidence_id=self.reference)

    malformed = MalformedReferencePort()
    references = ('https://synthetic.invalid/?token=fixture-secret', None, ['fixture-secret'])
    rejections = []
    for reference in references:
        malformed.reference = reference
        independent = investigate_chart(issue, check, malformed, now=100)
        assert independent['conclusion']['state'] == 'unknown'
        assert independent['conclusion']['evidence'] is None
        assert 'fixture-secret' not in json.dumps(independent)
        monitor = ReleaseMonitor(ReleasePlan(check, 100, 1000))
        rejected = monitor.tick(100, malformed)
        assert rejected['state'] == 'unknown' and rejected['evidence'] is None
        assert monitor.seen_evidence == set(check.observer_evidence)
        rejections.append({'reference_type': type(reference).__name__,
                           'independent': independent['conclusion'], 'release': rejected})

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
    print(json.dumps({'source_base': '0ce3d8561cbb1a5f16bc10a5e804bb72f9fd8882',
        'chart_checks_sha256': hashlib.sha256(Path('triage/chart_checks.py').read_bytes()).hexdigest(),
        'transport': 'actual loopback HTTP/Selenium waits; fake DOM and synthetic malformed adapter injection',
        'browser_model_video': 'NOT RUN', 'observer_actions': [e.action for e in issue.events],
        'reference_rejections': rejections, 'fresh_independent': independent,
        'same_check_release': results, 'cadence': 300, 'bounded_end': monitor.stopped,
        'observer_unchanged': True}, indent=2))
finally:
    server.shutdown()
    server.server_close()
    worker.join(2)
