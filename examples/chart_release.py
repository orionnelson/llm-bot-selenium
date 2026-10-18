"""Run with python -m examples.chart_release. Entirely synthetic; no live jobs."""
from dataclasses import asdict, replace
import json

from triage.core import Action, Context
from triage.chart_checks import (ChartBinding, ChartView, SyntheticObserver, ChartCheck,
                                 investigate_chart, ReleasePlan, ReleaseMonitor)


class SyntheticChartBrowser:
    session = 'synthetic-bot'

    def __init__(self, view):
        self.view = view
        self.routes = []

    def read_chart(self, route, binding):
        self.routes.append(route)
        return self.view


def main():
    binding = ChartBinding(Context('synthetic', 'test', 'checkout', 0, 2000),
                           Action('overview', 'invocation_health'), 'error-rate', 'percent',
                           (('environment', 'release'),))
    observed = ChartView(binding, 'observer-1', 100, 100, 0)
    observer = SyntheticObserver('synthetic-sre', [binding], consent=True)
    observer.record('navigate', 'dashboard', observed)
    observer.record('shortcut-open-chart', 'dashboard', observed)
    issue = observer.stop()
    check = ChartCheck.from_issue(issue, 1, sre_validated=True, now=100)
    bot = SyntheticChartBrowser(replace(observed, evidence_id='investigation-1', value=5))
    investigation = investigate_chart(issue, check, bot, now=100)
    monitor = ReleaseMonitor(ReleasePlan(check, 100, 1600))
    outcomes = []
    for now, value, state in [(100, 0, 'ready'), (400, 5, 'ready'),
                               (700, 5, 'ready'), (1000, None, 'loading'), (1300, 0, 'ready')]:
        bot.view = replace(observed, evidence_id='release-' + str(now), captured_at=now,
                           sample_at=now, value=value, state=state)
        outcomes.append({'at': now, **monitor.tick(now, bot)})
    assert monitor.tick(1600, bot) is None and monitor.stopped
    print(json.dumps({'evidence_kind': 'deterministic synthetic, not actual browser/model',
                      'issue': asdict(issue), 'check': asdict(check),
                      'investigation': investigation, 'release': outcomes,
                      'stopped_at_end': monitor.stopped, 'bot_routes': bot.routes}, indent=2))


if __name__ == '__main__':
    main()
