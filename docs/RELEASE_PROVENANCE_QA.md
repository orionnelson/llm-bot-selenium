# Keep the complete observed issue out of fresh release evidence

Base: blue-master `48e644421a81ab75a1c83a9fb07b7e174d20e70d`.

Two distinct observed pages produce `earlier-observer` and `last-observer`.
The SRE validates the final chart. Previously a bounded release tick accepted
`earlier-observer` as healthy (or failure), even though independent investigation
already rejected it. `ChartCheck.from_issue` now retains all bounded semantic
observer evidence references. ReleaseMonitor seeds its existing replay set with
those references plus the final source. No observer page text or WebDriver ID is
newly exported. A check constructed directly with four legacy arguments still
works, but only knows its supplied source; use `from_issue` for full provenance.

## Executed evidence

- Before: two regression subcases falsely returned healthy/failure; three new
  constructor-validation subcases errored because the new field did not exist.
- After: 185 Python tests = **180 PASS / 5 opt-in actual-browser SKIP**.
- **179 frontend PASS**; TypeScript and Vite build PASS; existing bundle advisory.
- Evaluation: 60/60 diagnosis pairs and 60/60 healthy counterexamples; connected
  synthetic chart-release example PASS; Python compilation and whitespace PASS.
- `RELEASE_PROVENANCE_DEMO.json`: actual temporary loopback HTTP with real Selenium
  waits and explicitly fake DOM driver. Navigation + shortcut -> validated check
  -> earlier-ID rejection in independent investigation AND release tick -> fresh
  healthy -> fresh failure -> deduped failure -> bounded end, all asserted.
- Full suite initially exposed an existing journey test DNS mock intercepting
  loopback HTTP resolution and redirecting it to the public fixture IP. It also
  reproduced in an isolated rerun. Test-only fix preserves real loopback DNS
  while mocking public lookup; no product URL/network policy was changed.
- First npm install omitted dev dependencies in this production environment;
  reran `npm ci --include=dev --ignore-scripts`, then tests/build passed.

Reproduce from repository root (Selenium from requirements.lock):

```sh
python -m unittest discover -s tests -v
python evaluate.py
python -m examples.chart_release_demo
python -m compileall -q triage tests
cd ui && npm ci --include=dev --ignore-scripts && npm test && npm run build
```

## Boundaries

This is the shared Python check/release library, with no release-monitor UI or
live scheduler. The existing synthetic chart HTML is not changed. Fresh rendered
component screenshot acceptance is **not complete**: local browser launch was
last blocked by missing libnspr4.so, and remote Grid cannot access the separate
process's deliberately loopback-only fixture. Those unchanged runtime blockers
were not re-probed or bypassed; no old image is substituted for new evidence.
Actual CLI/HTTP execution above proves logic, not browser rendering, model
inference, video or production acceptance. Native independent review failed
current gateway authentication; parent review only. No major UI work, deployment,
recording, alert destination, main release or shared-model change.

Eight insertions/two deletions in product source: **+6 net lines**, no dependency,
framework or scheduler. The tuple is bounded at 100 events and identifiers are
validated with existing guards. IDs alone cannot defeat a dishonest adapter
inventing fresh IDs. All full-product UC1/UC2/Studio/handoff gates remain open.
