# Preserve chart-read browser identity

The shared chart adapter previously checked isolation before reading, but did not verify that WebDriver identity remained the same during navigation or DOM collection. A replacement/rebound driver could supply a healthy or failing chart that was then attributed to the original observer or independent bot session.

`SeleniumChartPort` now snapshots its driver-derived session identity before navigation and before visible-chart collection, rejecting changed or missing identity before returning evidence. Capture appends nothing; independent investigation and the same reusable release check return unknown with no trusted evidence. Failed reads do not contaminate release evidence dedupe. A subsequent stable separate-session read can recover normally. Six net product lines; no new dependency, schema, scheduler, backend, transport or UI.

## Fresh executed demonstration

`CHART_SESSION_DEMO.json` records a fresh standalone execution through actual loopback HTTP and Selenium waits with a fake DOM. It contains the changed source SHA-256 and fresh remote base. The runner is `docs/chart_session_demo.py`; from the repository root run `python docs/chart_session_demo.py`.

1. A fake driver's identity changes during capture: rejected, observer history unchanged.
2. Stable consented navigation + semantic shortcut produce an issue and explicit SRE-validated check.
3. Fake bot identity changes during navigation to match the observer: independent investigation and release tick return unknown/no evidence, report once, no dedupe contamination.
4. Stable separate bot independently navigates the alternative route and verifies failure.
5. The SAME check recovers and exercises failure, dedupe, recovery, loading/unknown, recovery and bounded end using a fake clock. No sleeps or live monitor.

Six pre-fix assertions failed in the two new HTTP/fake-DOM tests, without follow-on test-state errors. Tests cover replacement/missing capture identity, navigation/payload changes, both healthy and failure values, unknown reporting, evidence set preservation and stable recovery/end.

## Verification and limits

- Full Python suite: 195 passed, 5 opt-in actual-browser skipped (200 total).
- Frontend: 179 passed; TypeScript/Vite build passed, existing >500 kB bundle advisory retained.
- Deterministic evaluation: 60/60 diagnoses and 60/60 healthy counterexamples; connected synthetic UC1/UC2 example passed.
- Python compilation and whitespace checks passed.

This API has no UI control. Fresh related chart screenshots are INCOMPLETE: the fixture was not rendered; last verified local Chromium lacks libnspr4.so and the remote Grid cannot reach this separate loopback-only fixture. No old screenshots substituted or security/network boundary changed. No new rendered-browser, model, video or production acceptance. Independent reviewer launch was actually blocked by gateway-token mismatch; parent review only.

These are boundary comparisons, not atomic WebDriver transactions. A change-and-revert between checks is undetected. The guard cannot undo navigation already performed or make shared/rebound drivers safe: callers must still own separate isolated drivers and must not replace them during an operation. This does not authenticate a malicious adapter or invent evidence authenticity. No private recording, production deployment/monitor, shared-model reload, canonical DAG/deployed Studio change or main release. Backend Python DAG remains authoritative. Full UC1/UC2, expanded Studio and handoff gates remain open.

## Rerun regression suite

```sh
python -m unittest discover -s tests -v
python evaluate.py
python -m examples.chart_release
python docs/chart_session_demo.py
cd ui && npm ci --include=dev --no-audit --no-fund && npm test && npm run build
```
