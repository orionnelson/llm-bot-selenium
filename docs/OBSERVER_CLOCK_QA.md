# Observer sample chronology

The consenting synthetic observer now rejects a sample timestamp later than its own capture before appending an event. Loading/missing evidence remains recordable when chronologically valid; stale/expired evidence remains subject to existing interpretation guards. This is representation consistency, not timestamp authenticity or clock accuracy.

The same recorder validates complete issue history during `ChartCheck.from_issue` and consented Studio export. A valid final chart must not hide an impossible earlier sample. Existing evaluator rejection for independently fetched post-capture samples is unchanged.

## Execute

```sh
python -m unittest discover -s tests -v
python evaluate.py
python -m examples.chart_release
PYTHONPATH=.:tests python docs/observer_clock_demo.py
cd ui && npm ci --include=dev --no-audit --no-fund && npm test && npm run build
```

Five new pre-fix failed assertions reproduced across three methods. Full regression: 218 Python PASS / 5 opt-in actual-browser SKIP (223 total); 179 frontend PASS; TypeScript/Vite build PASS with existing chunk advisory. An older test expected impossible data to remain recordable; updated it to assert earlier rejection and preserve forged-bundle/evaluator checks.

`OBSERVER_CLOCK_DEMO.json` is fresh actual loopback HTTP/Selenium-waits/fake-DOM output. Runner creates separate SRE/bot identities, captures navigation + semantic shortcut, rejects impossible sample in ready/loading/missing states for capture/conversion/Studio export, restores same observer, then investigates an alternative route and reuses SAME check for bounded 300-second failure/dedupe/recovery/loading/end ticks. No sleeps/live monitor.

The changed APIs have no visual UI. Fresh related-chart screenshots remain INCOMPLETE: historical local libnspr4.so / remote Grid-to-development-loopback blockers retained, not retried or bypassed. No previous image substituted. No new rendered-browser/model/video acceptance or independent reviewer success: native delegation gateway token mismatch. Full UC1/UC2/expanded Studio/handoff gates remain OPEN. No owner services, canonical DAG, recordings, global models, production or main-release changes.
