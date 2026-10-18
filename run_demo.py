"""Produce reproducible synthetic cold/learned/recovery/monitoring artifacts."""
from dataclasses import asdict, replace
from pathlib import Path
import argparse
import json
import time

from triage.core import (Context, MockPlanner, compile_skill, export_script,
                         explain_trace, investigate, replay, run_with_fallback, save_trace, validate_skill)
from triage.audit import Audit, verify_audit
from triage.fixtures import FixturePort
from triage.monitor import Monitor
from triage.registry import Registry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/demo")
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    now = 10000
    ctx = Context("demo-account", "us-east-1", "checkout", 9000, 9900)
    start = time.perf_counter()
    audit = Audit(out / "audit.jsonl")
    cold = investigate(FixturePort(), MockPlanner(), ctx, "training-001", "Why is checkout failing?", now=lambda: now, audit=audit)
    cold_ms = (time.perf_counter() - start) * 1000
    skill, contribution = compile_skill(cold)
    heldout = replace(ctx, function="payments", start=8000, end=8900)
    validate_skill(skill, [(FixturePort(), heldout, "heldout-002", "likely-dependency-timeout")], now=lambda: now)
    registry = Registry(out / "skills.sqlite")
    skill_version = registry.publish("dependency-triage", skill)
    skill = registry.load("dependency-triage", skill_version)
    start = time.perf_counter()
    warm = replay(skill, FixturePort(), replace(ctx, function="orders"), "fresh-003", now=lambda: now, audit=audit)
    warm_ms = (time.perf_counter() - start) * 1000
    drift = run_with_fallback(skill, FixturePort("timeout", ui="mock-v2"), MockPlanner(), ctx,
                              "changed-004", "Why is checkout failing?", now=lambda: now)
    monitor = Monitor()
    contexts = [replace(ctx, function=name) for name in ["dependency", "throttling", "timeout", "no-data", "expired"]]
    reports = monitor.sweep(contexts, lambda c: FixturePort(c.function, expired=c.function == "expired"), now=lambda: now)
    for name, trace in [("cold", cold), ("warm", warm), ("drift", drift)]:
        save_trace(trace, out / (name + "-trace.json"))
    for name, data in [("skill", asdict(skill)), ("query-contribution", contribution),
                       ("investigation-explanation", explain_trace(cold)), ("monitor", reports)]:
        (out / (name + ".json")).write_text(json.dumps(data, indent=2) + "\n")
    export_script(skill, out / "learned_selenium_skill.py")
    summary = {"scope": "deterministic synthetic demo; no live LLM, browser or SSO used",
               "cold": {"actions": len(cold.observations), "planner_calls": cold.model_calls, "ms": cold_ms, "finding": cold.result.failure},
               "warm": {"actions": len(warm.observations), "planner_calls": warm.model_calls, "ms": warm_ms, "finding": warm.result.failure},
               "drift": {"mode": drift.mode, "finding": drift.result.failure},
               "skill_sha256": skill.fingerprint(), "skill_version": skill_version,
               "audit_events": len(verify_audit(out / "audit.jsonl")), "monitor_resources": len(reports)}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
