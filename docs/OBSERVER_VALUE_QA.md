# Nonnegative chart evidence at the observer boundary

The existing chart-check product evaluates nonnegative numeric metrics. Previously its recorder accepted negative numbers, allowing an invalid earlier chart to survive full-history check conversion or be exported as Studio provenance when the final chart was valid. The shared recorder now enforces the same nonnegative domain before appending. One condition and error-message replacement; zero net product lines, no new dependency/schema/framework.

Missing values remain recordable as uncertainty; signed zero, zero and positive finite values remain accepted. Loading/missing evidence with a negative numeric value is rejected rather than repaired or clamped. This does not add support for signed metrics, prove evidence authenticity or root cause.

## Run

```sh
python -m unittest discover -s tests -v
PYTHONPATH=.:tests python docs/observer_value_demo.py
python evaluate.py
python -m examples.chart_release
cd ui && npm ci --include=dev --no-audit --no-fund && npm test && npm run build
```

Fresh output `OBSERVER_VALUE_DEMO.json` includes the exact changed-module SHA-256 and remote baseline. Actual loopback HTTP/Selenium waits with fake DOM: consented navigation+shortcut creates issue; negative ready/loading/missing input refuses capture/conversion/consented Studio export; no invalid event appended; restoring same observer works. Separate bot chooses alternative entity route and returns numeric failure. SAME SRE-validated check runs bounded cadence300 failure/dedupe/recovery/loading unknown/recovery/end with a caller fake clock. No live scheduler/alert send.

## Evidence limits

The affected recorder/conversion/export APIs have no visual component. CLI/API evidence demonstrates them directly. Fresh related-chart screenshot gate remains INCOMPLETE: fixture not freshly rendered; historical local missing libnspr4.so / remote Grid-to-development-loopback limitations are carried, not newly probed or bypassed. No old screenshots substitute for this build. No new rendered-browser/model/video acceptance claimed. Original owner Studio services/source/Grid/canonical DAG/recordings remain untouched; backend DAG stays canonical. Complete UC1/UC2 and expanded Studio/fullgraph/parallel/replay/handoff gates remain OPEN.
