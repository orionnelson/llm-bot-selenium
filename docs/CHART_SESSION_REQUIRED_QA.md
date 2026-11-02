# Require identifiable separate chart sessions

Both independent SRE investigation and the SAME reusable bounded release check
now apply the existing semantic session identifier guard before any adapter read.
Previously a stable None/empty/numeric/malformed wrapper session passed inequality
and post-read equality checks, returning false trusted healthy/failure results.
Invalid identity raises GuardError (as shared-session misuse already does), not
a monitoring result. No navigation, cadence-slot consumption, evidence/dedupe or
last-capture update occurs. Caller clock tracking still advances. A valid separate
identity can resume at the same due time. Stop/end/not-due calls remain no-ops.

Two product lines; no new dependency/schema/framework/scheduler. SeleniumChartPort
already validates driver-derived IDs; this protects other adapters/wrappers too.
This validates syntax/isolation identity, not identity authenticity or authorization.

## Reproduce

```sh
python -m unittest discover -s tests -v
PYTHONPATH=.:tests python docs/chart_session_required_demo.py
python evaluate.py
python -m examples.chart_release
cd ui && npm ci --include=dev --no-audit --no-fund && npm test && npm run build
```

Pre-fix: 15 failed assertions, zero errors in the two new methods.
Post-fix: 204 Python PASS / 5 opt-in actual-browser SKIP (209 total), 179 frontend
PASS, TypeScript/Vite build PASS (existing bundle advisory), 60/60 diagnoses and
60/60 healthy counterexamples. Actual standalone loopback HTTP/Selenium waits with
fake DOM covers consented observation/shortcut, explicit validation, invalid
sessions rejected before read, same-slot restoration, separate alternative-route
investigation, switched sessions, failure/dedupe/recovery/unknown/end/Stop.
Output CHART_SESSION_REQUIRED_DEMO.json records exact changed-source SHA-256.

## Acceptance boundaries

Fresh screenshot gate INCOMPLETE: affected consumer API has no UI; related chart
fixture not freshly rendered. Last verified local missing-libnspr4.so and remote
Grid-to-separate-loopback fixture blockers are carried, not re-probed/bypassed.
No previous images substitute for fresh evidence. Fake DOM is not browser/model/
video acceptance. Complete UC1/UC2 and expanded Studio graph/parallel/capture/
replay/handoff remain OPEN; development remains enabled. Owner sources/services/
canonical DAG/Grid and existing browser sessions preserved. Independent native
review attempt blocked gateway1008/token mismatch; author scope review only.
