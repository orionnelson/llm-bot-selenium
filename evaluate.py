"""Seeded fixture matrix, not a live-model or browser benchmark."""
from dataclasses import replace
from pathlib import Path
import argparse
import json
import random
from triage.core import (Context, MockPlanner, compile_skill, investigate, replay,
                         run_with_fallback, validate_skill)
from triage.fixtures import FixturePort


class ReorderedPort(FixturePort):
    def __init__(self, *args, seed=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.seed = seed

    def catalog(self):
        rows = super().catalog()
        random.Random(self.seed).shuffle(rows)
        return rows


EXPECTED = {"dependency": "likely-dependency-timeout", "throttling": "likely-throttling",
            "timeout": "likely-function-timeout"}


def evaluate():
    ctx = Context("demo-account", "us-east-1", "training", 9000, 9900)
    rows = []
    for kind, expected in EXPECTED.items():
        for seed in range(5):
            training = investigate(ReorderedPort(kind, seed=seed), MockPlanner(), ctx,
                                   f"training-{kind}-{seed}", "Investigate", now=lambda: 10000)
            skill, contribution = compile_skill(training)
            heldout = replace(ctx, function="heldout")
            validate_skill(skill, [(ReorderedPort(kind, seed=seed+100), heldout,
                                   f"heldout-{kind}-{seed}", expected)], now=lambda: 10000)
            for index in range(4):
                context = replace(ctx, function=f"function-{index}", start=8000-index*100, end=8900-index*100)
                cold = investigate(ReorderedPort(kind, seed=seed+index+1000), MockPlanner(), context,
                                   f"cold-{kind}-{seed}-{index}", "Investigate", now=lambda: 10000)
                warm = replay(skill, ReorderedPort(kind, seed=seed+index+1000), context,
                              f"warm-{kind}-{seed}-{index}", now=lambda: 10000)
                # Counterexample: never retain the old diagnosis on a healthy window.
                changed = run_with_fallback(skill, ReorderedPort("healthy", seed=seed), MockPlanner(), context,
                                            f"changed-{kind}-{seed}-{index}", "Investigate", now=lambda: 10000)
                rows.append({"kind": kind, "seed": seed, "resource": index,
                             "expected": expected, "cold": cold.result.failure, "warm": warm.result.failure,
                             "cold_actions": len(cold.observations), "warm_actions": len(warm.observations),
                             "cold_planner_calls": cold.model_calls, "warm_planner_calls": warm.model_calls,
                             "counterexample": changed.result.failure, "counterexample_mode": changed.mode})
    return {"scope": "60 deterministic synthetic pairs, 15 held-out skill validations; not independent real-world incidents",
            "cases": len(rows), "diagnosis_matches": sum(r["cold"] == r["warm"] == r["expected"] for r in rows),
            "healthy_counterexamples_correct": sum(r["counterexample"] == "no-failure-observed" and r["counterexample_mode"] == "discovery" for r in rows),
            "cold_planner_calls": sum(r["cold_planner_calls"] for r in rows),
            "warm_planner_calls": sum(r["warm_planner_calls"] for r in rows),
            "cold_actions": sum(r["cold_actions"] for r in rows), "warm_actions": sum(r["warm_actions"] for r in rows),
            "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/validation/evaluation.json")
    args = parser.parse_args()
    result = evaluate()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
    if result["diagnosis_matches"] != 60 or result["healthy_counterexamples_correct"] != 60:
        raise SystemExit(1)
