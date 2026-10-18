"""Loopback synthetic chart DOM adapter; no listeners or real-site selectors.

Only explicitly submitted semantic actions are recorded. Never reads page source,
keys, cookies, storage or arbitrary text. Caller owns separate isolated drivers.
"""
from dataclasses import asdict
import json
from urllib.parse import urlencode, urlsplit

from .chart_checks import ChartBinding, ChartView, identifier
from .core import Action, Context, GuardError
from .selenium_port import SeleniumPort


def binding_from_data(data):
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
        if route not in ('dashboard', 'entity-chart') or urlsplit(self.driver.current_url).path != '/chart/' + route:
            raise GuardError('unexpected synthetic chart route')
        element = self._wait('[data-chart-view]')
        self._origin_check()
        if not element.is_displayed():
            raise GuardError('chart evidence is not visible')
        try:
            payload = element.get_attribute('data-chart-view')
            text = element.text
            self._origin_check()
            if not payload or len(payload) > 8192 or len(text) > 80:
                raise ValueError('chart payload budget')
            data = json.loads(payload)
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
