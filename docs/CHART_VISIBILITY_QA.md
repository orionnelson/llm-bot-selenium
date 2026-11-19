# Chart visibility during evidence collection

The consenting SRE and independent bot must not accept a chart which becomes hidden while its payload/value are collected. Recheck the existing Selenium element's displayed state after collecting text; reject before constructing a ChartView. All capture/investigation/release callers reuse this guard. Two production lines, no new dependency, interface or scheduler.

Before: chart initially displayed, numeric text read succeeds, page hides it; adapter can still return healthy evidence. After: capture appends no event, independent investigation and release tick return unknown without a trusted evidence reference or dedupe contamination. A later visible fresh chart recovers; failures report, repeated failures dedupe, release end stops. This is a second visibility boundary, NOT an atomic DOM snapshot: changes after the last check or hide/reappear between checks remain undetectable.

## Executed on fresh remote c80df75844e5e23f59247c5881ea0805cc511622

- Two new regression tests failed before the fix: missing observer rejection and false healthy independent conclusion.
- `python -m unittest discover -s tests -v`: 185 PASS / 5 opt-in browser SKIP / 190 total.
- `cd ui && npm ci --include=dev --no-audit --no-fund && npm test`: 179 PASS.
- `npm run build`: TypeScript/Vite PASS, existing bundle-size advisories.
- `python evaluate.py`: 60/60 diagnoses and 60/60 healthy counterexamples.
- `python -m examples.chart_release`, compileall and git diff whitespace check: PASS.
- `CHART_VISIBILITY_DEMO.json`: separate executed temporary loopback HTTP/Selenium-wait/fake-DOM scenario and tested source SHA-256. Visibility transitions are simulated, not CSS-rendered browser proof. The observer regression specifically hides the chart after the text getter; integration regression tests the two visibility boundaries and fresh recovery.

## Evidence limits

Fresh affected-component screenshot gate INCOMPLETE/BLOCKED. No React code changed; there is no release-monitor UI. The related synthetic chart HTML was not rendered for this run. Last verified local browser lacks libnspr4.so; remote Grid cannot reach this separate loopback-only adapter fixture. Unchanged runtime/access failures were not repeatedly probed, no old image substituted and no sandbox/network/allowlist changes made. New real browser, model and video acceptance NOT RUN.

The owner-deployed instruction-retry repair/UI/Grid/canonical workflow/recordings/processes remain untouched. Existing Studio unit/build regressions pass, but full graph/parallel execution, complete UC1/UC2 model/browser acceptance and handoff remain open. No production monitor, deployment or live recording. Keep scheduled development enabled. Parent review only; native delegation/reviewer blocked by gateway token mismatch.
