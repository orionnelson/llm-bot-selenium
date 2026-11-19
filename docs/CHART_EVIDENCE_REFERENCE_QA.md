# Do not echo malformed chart evidence references

The reusable `ChartCheck.evaluate` boundary now returns `unknown` with no evidence reference for non-semantic references, before calling observation validation. A custom adapter previously made the independent conclusion echo a raw URL/token-shaped reference; non-string references raised `TypeError` in direct evaluation. The existing release consumer already rejected malformed IDs; its behavior and recovery are regression-tested with the SAME SRE-validated check.

Two production lines; no dependency, schema, executor, transport, UI or permission changes. Valid 1–100-character `[A-Za-z0-9_-]` references preserve the underlying evaluator contract, including retained references for loading/unknown observations. The release/recorder identifiers retain their pre-existing narrower limit. This validates syntax, not evidence authenticity; syntactically valid sensitive identifiers cannot be detected by this guard.

## Execute

```sh
python -m unittest discover -s tests -v
PYTHONPATH=.:tests python docs/chart_evidence_reference_demo.py
python -m examples.chart_release
python evaluate.py
cd ui && npm ci --include=dev && npm test && npm run build
```

Parent ran these with the existing project-local Selenium virtualenv and Node v24.14.0. Python: **207 PASS, 5 opt-in actual-browser SKIP, 212 total, zero errors/failures**. Frontend: **179 PASS**; TypeScript/Vite build PASS with existing bundle-size advisory. Deterministic evaluation: **60/60 diagnoses and 60/60 healthy counterexamples**. Compile and whitespace checks PASS. Before the fix: 6 failed assertions and 10 errors in the new reference subcases, zero unrelated failures. A mistaken `python -m triage.evaluate` invocation was corrected to the existing `python evaluate.py`; no product workaround.

## Fresh feature demonstration

[`CHART_EVIDENCE_REFERENCE_DEMO.json`](CHART_EVIDENCE_REFERENCE_DEMO.json) is the fresh executed output of [`chart_evidence_reference_demo.py`](chart_evidence_reference_demo.py), including SHA-256 of the affected source. Actual loopback HTTP/Selenium waits and a fake DOM produce a consenting navigation+shortcut issue and explicitly SRE-validated check. A custom-adapter wrapper injects URL-shaped, null and list references after a normal fixture read. Independent and release consumers return unknown/no reference; output never contains the synthetic secret marker. A fresh valid alternative-route investigation returns failure without changing the observer. The SAME check drives bounded 300-second release failure → deduped failure → recovery → loading unknown → recovery → end.

**No UI genuinely exists for this evaluator/API; no screenshot is invented.** The related chart fixture was not freshly rendered. Fresh affected-surface screenshot gate remains **INCOMPLETE**; prior local missing-libnspr4 / remote-Grid-to-separate-loopback-fixture limitations are carried as historical blockers, not re-probed or represented as current browser acceptance. No old screenshots substitute for this build. The executed adapter/CLI evidence is not real browser, model, recording/video, production or whole-product acceptance. All full UC1/UC2, expanded Studio and handoff gates remain open.

Owner Studio/deployed services/Grid/canonical DAG/recordings/processes were not changed. Latest remote `blue-master` baseline: `0ce3d8561cbb1a5f16bc10a5e804bb72f9fd8882`. Original OpenCode author completion inspected and directory status idle `{}`; no duplicate author or stale source overlay. Native independent review/delegation failed gateway-token mismatch; author review only. `main` release remains human-controlled.
