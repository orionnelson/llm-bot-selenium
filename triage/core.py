"""Planner-independent policy, evidence verification and trace-to-skill learning.

This is a research harness, not a production Dynatrace integration. Its typed
evidence rules are synthetic test oracles, not a general root-cause detector.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
import re


class GuardError(ValueError):
    """An independent policy or evidence gate refused the operation."""


class DriftError(GuardError):
    """A learned workflow no longer matches its observed UI contract."""


@dataclass(frozen=True)
class Context:
    account: str
    region: str
    function: str
    start: int
    end: int

    def check(self):
        for value in (self.account, self.region, self.function):
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value):
                raise GuardError("invalid context identifier")
        if type(self.start) is not int or type(self.end) is not int:
            raise GuardError("integer timestamps required")
        if self.start < 0 or not 0 < self.end - self.start <= 86400:
            raise GuardError("time range must be positive and at most 24 hours")


@dataclass(frozen=True)
class Action:
    page: str
    query: str


# No arbitrary SQL/DQL, JavaScript, shell, links, writes or model-supplied URLs.
# A real adapter needs independently reviewed semantic mappings, not these mock IDs.
CATALOG = (
    {"page": "overview", "query": "invocation_health", "description": "Invocation error rate and data freshness"},
    {"page": "logs", "query": "failure_events", "description": "Failure events and dependency correlation"},
    {"page": "capacity", "query": "throttling", "description": "Rule out invocation throttling"},
    {"page": "latency", "query": "duration", "description": "Duration compared with timeout"},
    {"page": "inventory", "query": "tags", "description": "Resource tags, usually navigation context"},
)
ALLOWED = frozenset((v["page"], v["query"]) for v in CATALOG)


@dataclass(frozen=True)
class Observation:
    action: Action
    context: Context
    evidence_id: str
    facts: dict
    captured_at: int
    ui_version: str
    session_valid: bool = True
    # Untrusted page text is deliberately separate from typed evidence.
    page_text: str = ""


@dataclass
class Diagnosis:
    failure: str
    evidence: list[str]
    ruled_out: list[str] = field(default_factory=list)
    confidence: str = "synthetic-rule-verified"


@dataclass
class Trace:
    incident: str
    context: Context
    ui_version: str
    observations: list[Observation]
    result: Diagnosis
    model_calls: int
    mode: str = "discovery"
    notes: list[str] = field(default_factory=list)


class Policy:
    def __init__(self, context: Context, *, max_age=300, now=None):
        context.check()
        self.context = context
        self.max_age = max_age
        self.now = now or (lambda: int(datetime.now(timezone.utc).timestamp()))

    def action(self, action: Action):
        if (not isinstance(action, Action) or not isinstance(action.page, str)
                or not isinstance(action.query, str) or (action.page, action.query) not in ALLOWED):
            raise GuardError("action is not in read-only query allowlist")

    def observation(self, obs: Observation, action: Action, version: str):
        self.action(action)
        if obs.action != action or obs.context != self.context:
            raise GuardError("observation context/action mismatch")
        if not obs.session_valid:
            raise GuardError("SSO session expired; stop and request approved reauthentication")
        if obs.ui_version != version:
            raise DriftError("UI contract changed")
        if type(obs.captured_at) is not int or not 0 <= self.now() - obs.captured_at <= self.max_age:
            raise GuardError("stale, future or missing observation timestamp")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", obs.evidence_id):
            raise GuardError("invalid evidence reference")
        if not isinstance(obs.facts, dict):
            raise GuardError("invalid evidence shape")


def _number(facts, key):
    value = facts.get(key)
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        return None
    return value


def diagnose(observations: list[Observation]) -> Diagnosis:
    """Synthetic evidence oracle; only fresh policy-checked observations belong here.

    Report likely mechanisms supported by fixture metrics/logs, not ultimate
    causal proof. Evidence is always collected again when a skill is reused.
    """
    by_query = {o.action.query: o for o in observations}
    health = by_query.get("invocation_health")
    if not health:
        return Diagnosis("unresolved", [], confidence="insufficient-evidence")
    inv = _number(health.facts, "invocations")
    errors = _number(health.facts, "errors")
    if inv is None or errors is None or errors > inv:
        return Diagnosis("unresolved", [health.evidence_id], confidence="invalid-or-missing-data")
    logs = by_query.get("failure_events")
    throttle = by_query.get("throttling")
    duration = by_query.get("duration")
    # Rejected/throttled requests need not appear as invocation Errors. Do not
    # infer health (or mere missing traffic) from Errors=0 or Invocations=0 alone.
    throttles = _number(throttle.facts, "throttles") if throttle else None
    if throttles is not None and throttles > 0:
        return Diagnosis("likely-throttling", [health.evidence_id, throttle.evidence_id])
    if throttles is None:
        return Diagnosis("unresolved", [health.evidence_id], confidence="throttle-evidence-missing")
    if inv == 0:
        return Diagnosis("no-data", [health.evidence_id, throttle.evidence_id], confidence="cannot-infer-health")
    if errors == 0:
        return Diagnosis("no-failure-observed", [health.evidence_id, throttle.evidence_id], confidence="observed-error-and-throttle-window-only")
    # Earlier branches return unless throttles is valid and zero.
    ruled = ["throttling"]
    if logs and logs.facts.get("event_code") == "DEPENDENCY_TIMEOUT" and logs.facts.get("correlated") is True:
        return Diagnosis("likely-dependency-timeout", [health.evidence_id, logs.evidence_id, throttle.evidence_id], ruled)
    if duration:
        p99, limit = _number(duration.facts, "p99_ms"), _number(duration.facts, "timeout_ms")
        if p99 is not None and limit and p99 >= limit and logs and logs.facts.get("event_code") == "FUNCTION_TIMEOUT":
            return Diagnosis("likely-function-timeout", [health.evidence_id, logs.evidence_id, duration.evidence_id], ruled)
    return Diagnosis("unresolved", [health.evidence_id], ruled, "insufficient-evidence")


class MockPlanner:
    """Deterministic planner for tests. This is NOT an LLM or zero-shot discovery."""
    def choose(self, goal, catalog, history):
        seen = {(o.action.page, o.action.query) for o in history}
        for row in catalog:
            if (row["page"], row["query"]) not in seen:
                return Action(row["page"], row["query"])
        return None


class StructuredPlanner:
    """Inject an approved model callback; raw model text never executes as code.

    callback receives a bounded goal/catalog and typed prior facts. A deployment
    must additionally enforce data minimization, egress approval and redaction.
    The independent Policy still validates the returned Action.
    """
    def __init__(self, callback):
        self.callback = callback

    def choose(self, goal, catalog, history):
        payload = {"goal": goal[:2000], "actions": catalog,
                   "observations": [{"query": o.action.query, "facts": model_facts(o)} for o in history]}
        response = self.callback(payload)
        if response == {"stop": True}:
            return None
        if not isinstance(response, dict) or set(response) != {"page", "query"}:
            raise GuardError("model output must be a structured page/query action")
        if not all(isinstance(v, str) for v in response.values()):
            raise GuardError("model action fields must be strings")
        return Action(**response)


def model_facts(observation):
    """Minimize model input: no arbitrary page/log strings or unknown fact keys.

    This strongly limits this demo's prompt-injection surface. Production logs
    require a separate approved redaction/extraction boundary; this is not a
    claim that arbitrary page content can be made safe by a text blacklist.
    """
    numeric = {"invocation_health": ("invocations", "errors"),
               "throttling": ("throttles",), "duration": ("p99_ms", "timeout_ms")}
    facts = {}
    for key in numeric.get(observation.action.query, ()):
        value = _number(observation.facts, key)
        if value is not None:
            facts[key] = value
    if observation.action.query == "failure_events":
        event = observation.facts.get("event_code")
        if event in ("DEPENDENCY_TIMEOUT", "FUNCTION_TIMEOUT", "THROTTLED", "UNKNOWN"):
            facts["event_code"] = event
        value = observation.facts.get("correlated")
        if type(value) is bool:
            facts["correlated"] = value
    return facts


def investigate(port, planner, context: Context, incident: str,
                goal: str, *, now=None, budget=8, audit=None) -> Trace:
    if type(budget) is not int or not 1 <= budget <= 30:
        raise GuardError("invalid investigation budget")
    policy = Policy(context, now=now)
    version = port.version()
    # Displayed catalog is untrusted; filter to operator-controlled action IDs.
    catalog = [{"page": r["page"], "query": r["query"],
                "description": next(x["description"] for x in CATALOG if (x["page"], x["query"]) == (r.get("page"), r.get("query")))}
               for r in port.catalog() if (r.get("page"), r.get("query")) in ALLOWED]
    observations, seen, calls = [], set(), 0
    for _ in range(budget):
        calls += 1
        action = planner.choose(goal, catalog, observations)
        if action is None:
            break
        policy.action(action)
        if action in seen:
            raise GuardError("planner repeated an action; bounded loop stopped")
        seen.add(action)
        if audit:
            audit.record("before-read", {"incident": incident, "action": asdict(action), "context": asdict(context)})
        obs = port.observe(action, context)
        policy.observation(obs, action, version)
        if any(o.evidence_id == obs.evidence_id for o in observations):
            raise GuardError("duplicate evidence ID")
        observations.append(obs)
        if audit:
            audit.record("verified-read", {"evidence": obs.evidence_id, "query": action.query, "facts": model_facts(obs)})
        result = diagnose(observations)
        if result.failure != "unresolved":
            break
    return Trace(incident, context, version, observations, diagnose(observations), calls)


def explain_trace(trace):
    """Evidence-linked hypothesis transitions, without pretending to read minds."""
    history, rows = [], []
    _, contribution = compile_skill(trace)
    for obs, value in zip(trace.observations, contribution):
        before = diagnose(history)
        history.append(obs)
        after = diagnose(history)
        if not value["retained"]:
            role = "not-needed-by-synthetic-oracle"
        elif after.ruled_out != before.ruled_out:
            role = "useful-rule-out"
        elif after.failure != before.failure:
            role = "diagnostic-transition"
        else:
            role = "supporting-evidence"
        rows.append({**value, "hypothesis_before": before.failure, "hypothesis_after": after.failure,
                     "ruled_out_after": after.ruled_out, "role": role,
                     "context": asdict(obs.context), "facts": model_facts(obs)})
    return rows


@dataclass
class Skill:
    schema: int
    intent: str
    ui_version: str
    actions: list[Action]
    learned_from: str
    expected_failure: str
    status: str = "candidate"
    validated_on: list[str] = field(default_factory=list)

    def fingerprint(self):
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


def compile_skill(trace: Trace) -> tuple[Skill, list[dict]]:
    if not trace.observations or trace.result.failure in ("unresolved", "no-data", "no-failure-observed"):
        raise GuardError("cannot learn a diagnostic skill without failure evidence")
    retained = list(trace.observations)
    contribution = []
    # Greedy ablation against the synthetic oracle, NOT proof of real causal value.
    # Retain rule-outs: diagnosis semantic signature includes those observations.
    signature = lambda result: (result.failure, sorted(result.ruled_out))
    for obs in trace.observations:
        without = [v for v in retained if v is not obs]
        useful = signature(diagnose(without)) != signature(trace.result)
        contribution.append({"query": obs.action.query, "page": obs.action.page,
                             "evidence": obs.evidence_id, "retained": useful,
                             "method": "synthetic-oracle-greedy-ablation"})
        if not useful:
            retained = without
    skill = Skill(1, "investigate-lambda-failure", trace.ui_version,
                  [o.action for o in retained], trace.incident, trace.result.failure)
    return skill, contribution


def replay(skill: Skill, port, context: Context, incident: str, *, now=None,
           candidate_validation=False, audit=None) -> Trace:
    if skill.schema != 1 or not skill.actions or len(skill.actions) > 30:
        raise GuardError("invalid skill schema or action count")
    if skill.status != "validated" and not candidate_validation:
        raise GuardError("candidate skill is not approved for reuse")
    if port.version() != skill.ui_version:
        raise DriftError("skill UI contract mismatch; rediscovery required")
    policy = Policy(context, now=now)
    observations, seen = [], set()
    for action in skill.actions:
        policy.action(action)
        if action in seen:
            raise GuardError("duplicate skill action")
        seen.add(action)
        if audit:
            audit.record("before-replay-read", {"incident": incident, "skill": skill.fingerprint(),
                                               "action": asdict(action), "context": asdict(context)})
        obs = port.observe(action, context)
        policy.observation(obs, action, skill.ui_version)
        if any(o.evidence_id == obs.evidence_id for o in observations):
            raise GuardError("duplicate evidence ID")
        observations.append(obs)
        if audit:
            audit.record("verified-replay-read", {"evidence": obs.evidence_id, "query": action.query, "facts": model_facts(obs)})
    result = diagnose(observations)
    if result.failure != skill.expected_failure:
        raise DriftError("fresh evidence does not support learned failure; rediscovery required")
    return Trace(incident, context, skill.ui_version, observations, result, 0, "learned-replay")


def validate_skill(skill: Skill, cases, *, now=None):
    # Failed revalidation must not leave a previously validated skill reusable.
    skill.status = "candidate"
    skill.validated_on = []
    if not cases or any(incident == skill.learned_from for _, _, incident, _ in cases):
        raise GuardError("held-out incidents required")
    passed = []
    for port, context, incident, expected in cases:
        result = replay(skill, port, context, incident, now=now, candidate_validation=True)
        if result.result.failure != expected:
            raise GuardError("held-out ground truth mismatch")
        passed.append(incident)
    skill.validated_on = sorted(set(passed))
    skill.status = "validated"


def run_with_fallback(skill, port, planner, context, incident, goal, *, now=None):
    try:
        return replay(skill, port, context, incident, now=now)
    except DriftError as exc:
        # Safety/session/context errors are deliberately NOT caught here.
        trace = investigate(port, planner, context, incident, goal, now=now)
        trace.notes.append("learned workflow invalidated: " + str(exc))
        return trace


def save_trace(trace: Trace, path):
    """Synthetic trace only; exclude untrusted raw page text from persisted output."""
    data = asdict(trace)
    for observation in data["observations"]:
        observation.pop("page_text", None)
    path.write_text(json.dumps(data, indent=2) + "\n")


def export_script(skill: Skill, path):
    if skill.status != "validated":
        raise GuardError("only validated skills can be exported")
    # Generate static code around serialized data; never interpolate model code.
    payload = json.dumps(asdict(skill), sort_keys=True)
    path.write_text('"""Generated synthetic Selenium skill; requires triage package. No login embedded."""\n'
                    'import json\nfrom triage.core import Action, Skill, replay\n'
                    'from triage.selenium_port import SeleniumPort\n'
                    f'DATA = json.loads({payload!r})\n'
                    'def run(driver, base_url, context, incident, *, now=None):\n'
                    '    values = dict(DATA)\n'
                    '    values["actions"] = [Action(**a) for a in values["actions"]]\n'
                    '    return replay(Skill(**values), SeleniumPort(driver, base_url), context, incident, now=now)\n')
