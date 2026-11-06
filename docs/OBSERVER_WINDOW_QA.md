# Keep observed samples inside the bound chart time window

Run from the repository root:

```sh
python -m unittest discover -s tests -v
PYTHONPATH=.:tests python docs/observer_window_demo.py
python evaluate.py
python -m examples.chart_release
cd ui && npm ci --include=dev --no-audit --no-fund && npm test && npm run build
```

The existing evaluator rejects out-of-window samples. This change applies the same condition before recording, so a malformed earlier event cannot hide behind a valid final chart during full-history check conversion or consented Studio provenance export. Reuses the shared recorder; two product lines, no dependency/schema/UI/scheduler change.

Fresh regression evidence: nine failing assertions before the fix across three methods (zero errors). After: 224 Python PASS / five opt-in actual-browser SKIP (229 total); 179 frontend PASS; TypeScript/Vite build PASS, existing bundle-size advisory. Evaluation: 60/60 diagnoses and 60/60 healthy counterexamples. Connected synthetic UC1/UC2 example and standalone demo PASS. Compilation and whitespace PASS.

Unit tests reject both lower and upper out-of-window sample times in ready/loading/missing states without appending. Both inclusive boundaries remain allowed, and capture time may be later than the bound sample window: capture is not incorrectly constrained to the historical chart range. Hand-built earlier invalid history rejects even with valid final chart and distinct evidence IDs.

The fresh standalone output in `OBSERVER_WINDOW_DEMO.json` records actual loopback HTTP/Selenium waits/fake DOM: consented navigation + shortcut -> issue -> invalid earlier sample refusal in capture/conversion/export -> same-observer restoration -> separate alternative-route bot failure -> SAME validated check bounded cadence300 failure/dedupe/recovery/loading unknown/recovery/end. Exact base and changed-module SHA-256 are recorded. No private page, live schedule or outbound alert.

Fresh affected-surface screenshot gate INCOMPLETE: these recorder/conversion/export APIs have no UI; executed API output is the real affected surface. Related chart fixture was not freshly rendered. Historical local libnspr4.so absence and remote Grid-to-development-loopback limitations carried without repeated probes or security bypass. No older image substituted. New rendered browser/model/video NOT RUN. Numeric/time-window consistency is not evidence authenticity or calibrated clocks. Full UC1/UC2 and expanded Studio/fullgraph/parallel/capture/replay/handoff remain OPEN.
