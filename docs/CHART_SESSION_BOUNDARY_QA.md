# Preserve separate browser identity at the consumer boundary

The SRE's issue and its explicitly validated ChartCheck remain the shared source
for independent investigation and bounded release checks. Both consumers now
snapshot the adapter's browser session before reading, then reject a changed
identity before interpreting or committing returned evidence. SeleniumChartPort
already guards its own driver; this closes the outer adapter/wrapper boundary.

A wrapper switching to the observer, another bot or a missing session formerly
returned healthy/failure. It now returns unknown with no trusted evidence.
Release evidence/last-capture state is untouched; cadence still advances normally.
A stable separate session can recover at the next due tick. Explicit Stop retains
precedence. No new executor, scheduler, dependency or permissions.

## Reproduce

```sh
python -m unittest discover -s tests -v
PYTHONPATH=.:tests python docs/chart_session_boundary_demo.py
python evaluate.py
python -m examples.chart_release
cd ui && npm ci --include=dev --no-audit --no-fund && npm test && npm run build
```

Executed: 202 Python passed / 5 opt-in actual-browser skipped (207 total);
179 frontend passed; TypeScript/Vite build passed (existing chunk-size warning).
Nine pre-fix failed assertions (six independent verdicts, three release verdicts).
The demo uses actual loopback HTTP/Selenium waits with a fake DOM and a switching
wrapper: observer navigation/shortcut -> issue -> validated check -> switched
independent/release reads rejected -> stable recovery -> same check failure,
dedupe, loading unknown, recovery and bounded end. Source SHA-256 is in the JSON.

## Evidence boundaries

This API-only consumer has no UI controls or release-monitor UI. Fresh rendered
related-chart screenshot gate remains INCOMPLETE: the last verified local
Chromium missing-libnspr4.so and remote-Grid-to-loopback fixture blockers are
carried forward, not retested or bypassed. No old screenshots substituted.
No new rendered-browser/model/video run or production recording/monitor/deploy.
Session comparison is not an atomic transaction: a change-and-revert between
checks is undetectable, and navigation already performed cannot be undone.
Adapters must still own separate drivers; this is not session authentication.
Full UC1/UC2/Studio/full-graph/parallel/replay/handoff gates remain OPEN.
