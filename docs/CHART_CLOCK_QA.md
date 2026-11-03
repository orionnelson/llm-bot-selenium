# Typed chart evaluation clock

A caller-supplied boolean, fractional/coerced timestamp, missing value, NaN or infinity must not mint a validated chart check or produce a trusted conclusion. `ChartView.verify` now rejects anything except a nonnegative exact Python integer before timestamp arithmetic. Shared check evaluation returns unknown; conversion raises GuardError; independent assistance does not navigate when its source interpretation is unknown. Release ticks already require monotonic integer clocks and retain that contract.

## Fresh execution

```sh
python -m unittest discover -s tests -v
python evaluate.py
python -m examples.chart_release
PYTHONPATH=.:tests python docs/chart_clock_demo.py
cd ui && npm ci --include=dev --no-audit --no-fund && npm test && npm run build
```

`CHART_CLOCK_DEMO.json` is actual current-source execution output, with SHA-256. The runner creates an isolated loopback HTTP fixture and uses Selenium waits with a fake DOM, through normal consented recorder → issue → SRE-validation → independent investigation APIs. Seven invalid clock categories reject conversion and yield unknown/no bot navigation. The SAME check then independently finds a failure through an alternative route and supports bounded 300-second release ticks: failure, dedupe, healthy recovery, loading unknown, healthy recovery, end. Server teardown runs in finally. Initial demo tried reading an unvisited fake driver's nonexistent URL; corrected the test runner to snapshot absence explicitly, without adding a navigation.

Before the fix, the three added tests reproduce 7 failed assertions and 6 errors; after it, they pass. Integer seconds remain accepted; float seconds are intentionally not silently truncated. This validates representation, not wall-clock accuracy or identity. Very large integer clocks still use existing timestamp freshness/context rules. It does not introduce scheduling, navigation execution, model inference or arbitrary code execution.

## Evidence limits

Affected API has no UI. Fresh affected-surface screenshot gate remains INCOMPLETE; related fixture was not freshly rendered. Last-verified local missing libnspr4.so and remote Grid-to-separate-loopback fixture limitations are carried, not re-probed or bypassed. No old screenshot substituted. No actual browser/model/video acceptance claimed. Backend-first Studio, observer/bot isolation, owner services, canonical DAG, production boundaries and main release controls remain unchanged. Full UC1/UC2 and expanded Studio/handoff remain open.
