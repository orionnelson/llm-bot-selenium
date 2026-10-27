# Reject malformed chart filters before trusting evidence

Base blue-master: `bc905099d6537ea1c53bbfd32d4ef5797c140de1`.

The shared JSON binding parser previously coerced arbitrary iterable filters:
`["ab"]`, `{"ab":"ignored"}` and `[{"a":1,"b":2}]` became the valid filter
`(("a", "b"),)`. Empty strings/objects became the valid unfiltered scope. Such
malformed chart evidence could be recorded or evaluated as healthy rather than
unknown. Request bindings could likewise reach the chart callback.

The parser now requires a JSON array of two-element JSON arrays **before**
converting to the existing immutable tuple. Existing identifier, duplicate-key,
filter-count, context and action checks remain authoritative. Correct empty
arrays and correctly encoded filters remain compatible. Python ChartBinding
construction is unchanged. Two added product lines; no dependency or schema
version change. This validates representation, not honesty of adapter data.

## Actual executed evidence

- Pre-fix regression failures: malformed filters accepted, invalid requests
  reached the chart callback, observer accepted them, and independent/release
  paths falsely classified healthy. See the dated development report for counts.
- Final Python: **183 PASS / 5 opt-in actual-browser SKIP / 188 total**.
- Frontend: **179 PASS**; TypeScript/Vite build PASS (existing bundle advisory).
- Evaluation: **60/60 diagnoses + 60/60 healthy counterexamples**; connected
  synthetic chart-release example, compilation and whitespace checks PASS.
- `CHART_FILTER_DEMO.json`: executed temporary loopback HTTP + real Selenium
  waits + explicitly fake DOM. Valid navigation/shortcut issue -> malformed
  request HTTP400 -> malformed capture rejected with zero events -> independent
  investigation unknown -> release unknown without dedupe contamination ->
  correctly encoded healthy recovery -> failure -> deduped failure -> bounded end.
  Includes exact changed source SHA-256. No wall-clock monitoring loop installed.

Reproduce (Python environment includes requirements.lock):

```sh
python -m unittest discover -s tests -v
python evaluate.py
python -m examples.chart_release
python -m compileall -q triage tests
cd ui && npm ci --include=dev --no-audit --no-fund && npm test && npm run build
```

## Evidence limits

This is a non-visual Python parser shared by the synthetic chart request/DOM
adapter; no release-monitor UI exists and no HTML/React component changed.
Fresh affected-surface screenshot gate remains **INCOMPLETE/BLOCKED**: previously
verified local Chromium cannot launch without libnspr4.so; the remote Grid cannot
reach this separate process's deliberately loopback-only fixture. These unchanged
blockers were not re-probed; no sandbox/allowlist relaxation, fixture deployment,
old screenshot substitution or invented UI. API/CLI evidence is not rendered
browser, actual model, video or whole-product acceptance. Parent review only;
independent review is not claimed. Existing owner UI, repair, recordings, DAG,
services, main and shared-model state are untouched. Both complete UC1/UC2,
expanded Studio and handoff gates stay open; development must remain enabled.
