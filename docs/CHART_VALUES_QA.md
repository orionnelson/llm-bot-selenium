# Numeric text stability across SRE and release checks

The shared loopback Selenium chart adapter now compares numeric text on the existing
post-read metadata recheck. A chart with unchanged metadata but changing text previously
allowed the first value to create an issue or produce an obsolete healthy/failure verdict.
No public API, schema, dependency, scheduler or execution framework change.

## Executed 2026-10-29 02:00 UTC

Latest remote base: f2facd8d1f4ae259174bb97d00f52bf8edc4370a.
Affected source SHA256: d09a8e9a14f67f113cd09e1da7459137aea685bd7e288e90ad21f522394169b1.

Commands, using existing project-local Python environment:

```sh
PYTHONPATH=.:tests ../demo/.venv/bin/python -m unittest test_chart_browser.ChartDOMTests.test_numeric_text_changed_during_collection_is_not_observed test_chart_browser.ChartDOMTests.test_changed_numeric_text_is_unknown_then_release_recovers -v
../demo/.venv/bin/python -m unittest discover -s tests -v
../demo/.venv/bin/python evaluate.py
../demo/.venv/bin/python -m examples.chart_release
../demo/.venv/bin/python -m compileall -q triage tests
(cd ui && npm ci --include=dev --no-audit --no-fund && npm test && npm run build)
git diff --check
```

Before fix: six failed assertions in the two new regression methods. After fix:
189 Python passed, five opt-in browser tests skipped (194 total); 179 frontend passed;
TypeScript/Vite build passed with existing bundle-size advisory; 60/60 diagnosis and
60/60 healthy evaluations; connected synthetic UC1/UC2 example, compile and whitespace passed.

## Feature demonstration

`CHART_VALUES_DEMO.json` is separately executed actual loopback HTTP/Selenium-wait output
using the real adapter and fake DOM/WebDriver. Synthetic navigation and semantic shortcut
create the issue and explicit SRE validation creates the reused check. Numeric text 0 -> 8
with metadata unchanged is rejected before observer insertion; separate-route investigation
and bounded release produce unknown/no trusted evidence, with no evidence-set contamination.
Stable fresh value recovers healthy; fresh failure reports once, repeated failure dedupes,
and the release end stops. Tests also cover 8 -> 0 and value disappearance.

No ReleaseMonitor UI exists; related synthetic chart HTML is not rendered in this evidence.
Fresh affected-component screenshot gate INCOMPLETE/BLOCKED: carried last verified local
Chromium missing libnspr4.so and remote Grid unable to reach this loopback-only fixture.
No repeated unchanged probes, security bypass, old screenshot substitution or fabricated UI.
The demonstration is not a rendered-browser, actual-model, video or production acceptance.

One extra text read for unchanged metadata. This is conservative raw-text stability,
not an atomic snapshot: changes after the check or away-and-back can escape detection;
numerically equivalent formatting changes can reject. Preserve existing privacy/consent,
separate sessions, context/freshness/expiry and stop controls. Parent review only; native
independent delegation unavailable due gateway token mismatch. Complete UC1/UC2 and
expanded Studio full-graph/parallel/replay/handoff remain open. No live monitor/deployment.
