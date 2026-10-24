"""Synthetic consenting observer -> independent chart check -> bounded release ticks.

No browser hooks, keystroke capture, model calls, scheduler or alert transport.
"""
from dataclasses import dataclass
import math
import re

from .core import Action, Context, GuardError, Observation, Policy


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value):
        raise GuardError('expected a semantic identifier, not raw page text or URL')


@dataclass(frozen=True)
class ChartBinding:
    context: Context
    action: Action
    chart: str
    label: str
    filters: tuple[tuple[str, str], ...] = ()

    def check(self):
        Policy(self.context).action(self.action)
        identifier(self.chart)
        identifier(self.label)
        if type(self.filters) is not tuple or len(self.filters) > 10:
            raise GuardError('bounded immutable filters required')
        keys = []
        for pair in self.filters:
            if type(pair) is not tuple or len(pair) != 2:
                raise GuardError('filter key/value pair required')
            for value in pair:
                identifier(value)
            keys.append(pair[0])
        if len(keys) != len(set(keys)):
            raise GuardError('duplicate filters')


@dataclass(frozen=True)
class ChartView:
    binding: ChartBinding
    evidence_id: str
    captured_at: int
    sample_at: int
    value: float | None
    state: str = 'ready'
    session_valid: bool = True
    ui_version: str = 'chart-v1'

    def verify(self, binding, now):
        binding.check()
        if type(self.session_valid) is not bool:
            raise GuardError('typed session state required')
        if self.binding != binding:
            raise GuardError('chart/entity/filters/time window mismatch')
        Policy(binding.context, now=lambda: now).observation(
            Observation(binding.action, binding.context, self.evidence_id, {},
                        self.captured_at, self.ui_version, self.session_valid),
            binding.action, 'chart-v1')
        if type(self.sample_at) is not int or not 0 <= now - self.sample_at <= 300 or self.sample_at > self.captured_at:
            raise GuardError('stale, future, post-capture or missing chart sample')
        if not binding.context.start <= self.sample_at <= binding.context.end:
            raise GuardError('sample outside bound chart time window')
        if self.state != 'ready':
            raise GuardError('chart loading or missing')
        if type(self.value) not in (int, float) or not math.isfinite(self.value) or self.value < 0:
            raise GuardError('missing or invalid chart value')


@dataclass(frozen=True)
class IssueEvent:
    action: str
    route: str
    view: ChartView


@dataclass(frozen=True)
class IssueBundle:
    observer_session: str
    events: tuple[IssueEvent, ...]


class SyntheticObserver:
    """Explicit semantic input only; no DOM/browser recording is installed."""
    def __init__(self, session, allowed, *, consent=False):
        identifier(session)
        if consent is not True or not allowed:
            raise GuardError('explicit synthetic observation consent and scope required')
        for binding in allowed:
            binding.check()
        self.session, self.allowed = session, tuple(allowed)
        self.events = []
        self.stopped = False

    def record(self, action, route, view):
        if self.stopped:
            raise GuardError('observation stopped')
        if action not in ('navigate', 'shortcut-open-chart') or route not in ('dashboard', 'entity-chart'):
            raise GuardError('only semantic navigation/shortcut actions allowed')
        if view.binding not in self.allowed:
            raise GuardError('page/chart outside consented scope')
        if len(self.events) >= 100:
            raise GuardError('issue event budget exhausted')
        # Keep loading/expired evidence for the issue; interpretation must fail closed.
        identifier(view.evidence_id)
        identifier(view.ui_version)
        if type(view.sample_at) is not int or type(view.session_valid) is not bool:
            raise GuardError('typed sample timestamp and session state required')
        if type(view.captured_at) is not int or (self.events and view.captured_at < self.events[-1].view.captured_at):
            raise GuardError('ordered integer event timestamps required')
        if view.state not in ('ready', 'loading', 'missing'):
            raise GuardError('invalid chart state')
        if view.value is not None and (type(view.value) not in (int, float) or not math.isfinite(view.value)):
            raise GuardError('typed numeric chart value required')
        self.events.append(IssueEvent(action, route, view))

    def stop(self):
        self.stopped = True
        return IssueBundle(self.session, tuple(self.events))


@dataclass(frozen=True)
class ChartCheck:
    binding: ChartBinding
    maximum: float
    source_evidence: str
    observer_session: str

    def __post_init__(self):
        self.binding.check()
        identifier(self.source_evidence)
        identifier(self.observer_session)
        if type(self.maximum) not in (int, float) or not math.isfinite(self.maximum) or self.maximum < 0:
            raise GuardError('explicit finite nonnegative maximum required')

    @classmethod
    def from_issue(cls, issue, maximum, *, sre_validated=False, now):
        if sre_validated is not True or not issue.events:
            raise GuardError('explicit SRE validation and observed chart required')
        if type(maximum) not in (int, float) or not math.isfinite(maximum) or maximum < 0:
            raise GuardError('explicit finite nonnegative maximum required')
        view = issue.events[-1].view
        view.verify(view.binding, now)
        return cls(view.binding, maximum, view.evidence_id, issue.observer_session)

    def evaluate(self, view, now):
        try:
            view.verify(self.binding, now)
        except GuardError as exc:
            return {'state': 'unknown', 'evidence': view.evidence_id, 'uncertainty': str(exc)}
        return {'state': 'healthy' if view.value <= self.maximum else 'failure',
                'evidence': view.evidence_id, 'value': view.value,
                'maximum': self.maximum, 'uncertainty': 'numeric chart condition only; not root cause'}


def investigate_chart(issue, check, bot, *, now):
    """Deterministic synthetic baseline, NOT model-led page understanding."""
    if not issue.events or issue.observer_session != check.observer_session:
        raise GuardError('check/issue provenance mismatch')
    if bot.session == issue.observer_session:
        raise GuardError('investigation requires a separate browser session')
    observed = issue.events[-1]
    if observed.view.evidence_id != check.source_evidence or observed.view.binding != check.binding:
        raise GuardError('check must derive from this observed chart')
    interpretation = check.evaluate(observed.view, now)
    if interpretation['state'] == 'unknown':
        return {'observed': interpretation, 'conclusion': interpretation, 'route': None}
    # Navigate via entity rather than replaying the person's dashboard shortcut (or vice versa).
    route = 'entity-chart' if observed.route == 'dashboard' else 'dashboard'
    try:
        fresh = bot.read_chart(route, check.binding)
        conclusion = check.evaluate(fresh, now)
    except Exception:
        return {'observed': interpretation, 'route': route,
                'conclusion': {'state': 'unknown', 'evidence': None, 'uncertainty': 'chart read failed'}}
    if fresh.evidence_id == check.source_evidence:
        conclusion = {'state': 'unknown', 'evidence': fresh.evidence_id, 'uncertainty': 'reused observer evidence'}
    return {'observed': interpretation, 'conclusion': conclusion, 'route': route}


@dataclass(frozen=True)
class ReleasePlan:
    check: ChartCheck
    start: int
    end: int
    cadence: int = 300

    def __post_init__(self):
        self.check.binding.check()
        if type(self.start) is not int or type(self.end) is not int or not 0 <= self.start < self.end <= self.start + 86400:
            raise GuardError('release window must be bounded to at most 24 hours')
        if type(self.cadence) is not int or not 1 <= self.cadence <= 3600:
            raise GuardError('bounded integer cadence required')


class ReleaseMonitor:
    """Caller-driven synthetic ticks; no sleeps, persistent jobs or alert sends.

    shortcut: dedupe is in-memory per release, add transactional state before live use.
    """
    def __init__(self, plan):
        self.plan = plan
        self.next_due = plan.start
        self.stopped = False
        self.last_state = None
        self.last_tick = -1
        # At most one read per cadence slot in the <=24h release window.
        self.seen_evidence = {plan.check.source_evidence}

    def stop(self):
        self.stopped = True

    def tick(self, now, bot):
        if type(now) is not int or now < self.last_tick:
            raise GuardError('monotonic integer clock required')
        self.last_tick = now
        if self.stopped or now >= self.plan.end:
            self.stopped = True
            return None
        if now < self.next_due:
            return None
        if bot.session == self.plan.check.observer_session:
            raise GuardError('monitor requires a separate browser session')
        # Skip missed slots rather than burst/replay; always collect current evidence.
        self.next_due = self.plan.start + ((now - self.plan.start) // self.plan.cadence + 1) * self.plan.cadence
        try:
            view = bot.read_chart('entity-chart', self.plan.check.binding)
            if self.stopped:
                return None
            identifier(view.evidence_id)
            result = self.plan.check.evaluate(view, now)
            if view.evidence_id in self.seen_evidence:
                result = {'state': 'unknown', 'evidence': view.evidence_id, 'uncertainty': 'reused evidence within this release'}
            self.seen_evidence.add(view.evidence_id)
            if not view.session_valid:
                self.stop()
        except Exception:
            if self.stopped:
                return None
            # Transport failures have no trusted evidence. Do not leak raw exception text.
            result = {'state': 'unknown', 'evidence': None, 'uncertainty': 'chart read failed'}
        result['duplicate'] = result['state'] == self.last_state
        result['report'] = result['state'] in ('failure', 'unknown') and not result['duplicate']
        self.last_state = result['state']
        return result
