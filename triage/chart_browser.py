"""Loopback synthetic chart DOM adapter; no listeners or real-site selectors.

Only explicitly submitted semantic actions are recorded. Never reads page source,
keys, cookies, storage or arbitrary text. Caller owns separate isolated drivers.
"""
from dataclasses import asdict
import json
from urllib.parse import urlencode, urlsplit
from uuid import uuid4

from .chart_checks import ChartBinding, ChartView, SyntheticObserver, identifier
from .core import Action, Context, GuardError
from .selenium_port import SeleniumPort


def _unique_fields(pairs):
    data = dict(pairs)
    if len(data) != len(pairs):
        raise ValueError('duplicate chart evidence fields')
    return data


def binding_from_data(data):
    if type(data['filters']) is not list or any(type(pair) is not list or len(pair) != 2 for pair in data['filters']):
        raise GuardError('filter list of key/value lists required')
    binding = ChartBinding(Context(**data['context']), Action(**data['action']),
                           data['chart'], data['label'], tuple(tuple(p) for p in data['filters']))
    if set(data) != {'context', 'action', 'chart', 'label', 'filters'}:
        raise GuardError('unexpected chart binding fields')
    binding.check()
    return binding


class SeleniumChartPort(SeleniumPort):
    @property
    def session(self):
        # Derive isolation identity from WebDriver, never a caller-provided alias.
        identifier(self.driver.session_id)
        return self.driver.session_id

    def read_visible(self, binding, route):
        binding.check()
        self._origin_check()
        url = self.driver.current_url
        if route not in ('dashboard', 'entity-chart') or urlsplit(url).path != '/chart/' + route:
            raise GuardError('unexpected synthetic chart route')
        element = self._wait('[data-chart-view]')
        self._origin_check()
        if self.driver.current_url != url:
            raise GuardError('chart URL changed during read')
        if not element.is_displayed():
            raise GuardError('chart evidence is not visible')
        try:
            payload = element.get_attribute('data-chart-view')
            text = element.text
            if element.get_attribute('data-chart-view') != payload:
                raise GuardError('chart evidence changed during read')
            if not element.is_displayed():
                raise GuardError('chart evidence became hidden during read')
            self._origin_check()
            if self.driver.current_url != url:
                raise GuardError('chart URL changed during read')
            if not payload or len(payload) > 8192 or len(text) > 80:
                raise ValueError('chart payload budget')
            data = json.loads(payload, object_pairs_hook=_unique_fields)
            if type(data) is not dict:
                raise ValueError('chart object required')
            actual = binding_from_data(data.pop('binding'))
            view = ChartView(binding=actual, value=json.loads(text) if text else None, **data)
            if actual != binding:
                raise ValueError('chart scope changed')
            return view
        except (ValueError, TypeError, KeyError):
            raise GuardError('invalid or mismatched synthetic chart evidence') from None

    def read_chart(self, route, binding):
        binding.check()
        if route not in ('dashboard', 'entity-chart'):
            raise GuardError('chart route not allowlisted')
        self._load('/chart/' + route + '?' + urlencode({'binding': json.dumps(asdict(binding))}))
        return self.read_visible(binding, route)

    def capture(self, observer, action, route, binding):
        # Consent, identity and scope checks happen BEFORE touching the person's DOM.
        if (observer.stopped or observer.session != self.session or binding not in observer.allowed
                or action not in ('navigate', 'shortcut-open-chart')
                or route not in ('dashboard', 'entity-chart')):
            raise GuardError('observation consent/session/action/scope refused')
        observer.record(action, route, self.read_visible(binding, route))

    def export_studio_session(self, issue, *, consent=False):
        """Explicit in-memory metadata export; no DOM read, file write or recording.

        Full chart evidence stays in the issue, not in the reusable click path.
        Studio imports this as unverified metadata, never as successful execution.
        """
        if (consent is not True or issue.observer_session != self.session
                or not 1 <= len(issue.events) <= 100):
            raise GuardError('export consent, matching observer and bounded issue required')
        # Reuse recorder validation: dataclasses alone do not establish trust.
        checked = SyntheticObserver(self.session, [e.view.binding for e in issue.events], consent=True)
        start = issue.events[0].view.captured_at
        events = []
        for index, event in enumerate(issue.events):
            checked.record(event.action, event.route, event.view)
            elapsed = (event.view.captured_at - start) * 1000
            if not 0 <= elapsed <= 86400000:
                raise GuardError('Studio export duration exceeds 24 hours')
            events.append({'id': 'event-' + str(index), 'elapsedMs': elapsed,
                           'action': event.action, 'url': self.base_url + '/chart/' + event.route})
        # Never serialize WebDriver's session ID, binding queries or evidence values.
        return {'version': 'triage-session/v1', 'id': 'observed-' + uuid4().hex,
                'mode': 'recorded', 'provenance': 'imported', 'url': events[0]['url'], 'events': events}
