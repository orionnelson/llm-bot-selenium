# Chart DOM integration QA — 2026-10-18 22:48 UTC run

Baseline: fetched actual remote `blue-master` `77d5ae9f08a9f800855d21d9207bcfe68fb17750`, not a prior source snapshot. `main` is human-controlled.

## Executed evidence

From repository root, using the existing project-local Selenium virtualenv:

```sh
python -m unittest discover -s tests -v
python -m compileall -q triage tests examples
python evaluate.py
python -m examples.chart_release
python browser_probe.py --browser edge --run
python browser_probe.py --browser chrome --run
```

- **80 tests: 78 PASS, 2 real-browser SKIP, 0 FAIL.** Complete log: `test-results-latest.txt`.
- New tests use actual loopback HTTP requests, real Selenium wait APIs and a fake DOM driver. They are **not real rendered browser tests**.
- UC1: visible numeric DOM + explicit semantic navigation/shortcut submissions produce an issue. A separate WebDriver identity independently takes the entity route; numeric failure evidence wins over unrelated misleading text. Person's URL remains unchanged.
- UC2: the exact observed/SRE-validated check drives release ticks at 300-second fake-clock intervals; failure reporting, repeat dedupe, recovery and end boundary tested. Existing explicit-stop, stale/context/drift/session/freshness suite retained.
- New DOM regressions: loading, missing, stale sample, changed filters/time range, UI drift, expired session, wrong origin, redirect during wait, hidden chart, malformed/non-object/oversized payload. Capture refuses stopped, mismatched-session, out-of-scope and raw-key actions before DOM reads.
- Existing seeded matrix remains 60/60 cold/reuse pairs and 60/60 healthy counterexamples; deterministic fixtures, not model inference.
- Compilation and staged whitespace checks pass.

## Browser and model acceptance: still OPEN

Both probes exit 2 / blocked: Edge + msedgedriver and Chrome + chromedriver are absent. New opt-in `test_actual_two_browser_chart_issue_and_bounded_release` is included in the existing browser probe path, but SKIPPED here. It creates two isolated drivers/profiles; neither actual browser journey nor Windows runtime was executed.

No actual model inference was added or run. Numeric interpretation and alternate-route selection remain deterministic. The adapter is synthetic loopback-only, not Dynatrace selectors, an event listener, automatic keyboard-shortcut detection, or production-ready monitoring. Semantic shortcut actions are explicitly submitted by the synthetic caller. Both full agreed acceptance gates remain open; do not disable development cron.

## Focused parent review

Reused `SeleniumPort` rather than duplicate origin/wait/navigation logic. Added no dependency, model switch, daemon, production access, profile reuse or raw page capture. Session identity comes from WebDriver itself. Tests/docs are separate from production code. Native independent reviewer could not start: gateway token mismatch; no independent-review success claimed.

Remaining limitations: fixed-window nonnegative scalar maximum, in-memory release dedupe, synchronous synthetic DOM contract. A real page needs a reviewed visible-data completion/freshness mapping; this adapter does not solve general asynchronous charts or infer root cause.
