# Connected chart contract slice — 2026-10-18 14:00 UTC

Historical contract baseline below. Current DOM integration and latest 78PASS/2SKIP evidence: [BROWSER_CHART_QA.md](BROWSER_CHART_QA.md).

## Executed locally

- `../demo/.venv/bin/python -m unittest discover -s tests -v`: **74 tests: 73 passed, 1 real-browser skipped**, zero failures. Includes 13 new chart-contract tests. Full output: `test-results-latest.txt`.
- `../demo/.venv/bin/python -m examples.chart_release`: genuine execution of the deterministic synthetic journey. Issue contains navigation + semantic shortcut; bot chooses entity-chart instead of dashboard; observed value 0 and independently read value 5 produce healthy → failure with distinct evidence IDs. The same validated check is reused at fake times 100/400/700/1000/1300; results healthy/failure/duplicate failure/loading-unknown/healthy. Release ends at 1600 without another read. No sleeps.
- `../demo/.venv/bin/python evaluate.py`: existing seeded harness retains 60/60 matching cold/reuse diagnoses, 60/60 healthy counterexamples, 281 cold versus 180 reused actions, zero warm planner calls. These are fixture results, not model benchmarks.
- `../demo/.venv/bin/python -m compileall -q triage tests examples`: passed.

These commands use the runner's existing project-local virtualenv. In a fresh clone, install `requirements.lock` in `.venv` and use `.venv/bin/python` instead.

## Acceptance progress, separately

**Use case 1:** synthetic consenting semantic observer → immutable issue timeline → numeric interpretation → independently chosen alternate route in a distinct synthetic session → fresh supported conclusion. Tests include withheld consent, disallowed shortcuts, stopped capture, scope mismatch, misleading raw-text exclusion, loading/missing/non-numeric data, stale/future samples and captures, changed labels/filters/time windows/entities, UI drift, expired sessions, shared-session refusal and transport uncertainty. No assertion of SRE private reasoning or root cause.

**Use case 2:** exactly the same check object binds chart/entity/filters/fixed time window and explicit maximum, with source evidence and SRE validation. Fake-clock ticks prove 300-second cadence, bounded start/end, missed-slot skipping, failure/unknown reports, repeated-state suppression, recovery/recurrence, reused-evidence refusal, read failures, session-expiry stop, explicit stop and clock-rollback rejection. Reporting policy is in-memory per-release state transitions: first failure/unknown reports, unchanged state suppresses, healthy resets. There is no alert transport.

## Not accepted / risks

- This is a **deterministic synthetic contract slice**, not full acceptance of either product journey. No human browser listener is installed. Semantic inputs are explicitly constructed; no arbitrary keypress/page-text/password/cookie/token fields exist. Production adapter redaction/storage/consent enforcement remains unimplemented.
- `read_chart` is a synthetic reader contract, not connected to `SeleniumPort` yet. Real Edge/Chrome execution remains skipped: no configured browser/driver pair. Windows is unexecuted. Existing mocked WebDriver wiring is not a browser pass.
- No actual model inference/page interpretation was run. Numeric threshold comparison and alternate-route selection are deterministic. Real-model adversarial page-text handling and actual chart loading/navigation acceptance remain gates.
- Charts use an explicitly fixed time window and nonnegative scalar maximum; no rolling-window transformation, screenshot-derived threshold, inferred health rule or root-cause claim.
- Caller-driven ticks do not isolate a blocked browser call. No persistent dedupe, live scheduler, background threads, production alerts, SSO reuse or model-service changes. Separate human plan/runtime/destination authorization is required before live use.
- Retained legacy `Monitor.sweep` can wait indefinitely for a hung adapter and omits account/region on blocked-result reports. Those are known defects in the separate earlier scaffold, not fixed by this slice. Existing mock UI pre-populates result JSON; it is not proof of asynchronous chart completion. Top-level origin checks do not provide pre-request browser egress isolation.

Next: connect the typed chart contract to an approved isolated synthetic browser fixture and run actual Edge + approved-model journey acceptance; do not enable production observation or a five-minute job.
