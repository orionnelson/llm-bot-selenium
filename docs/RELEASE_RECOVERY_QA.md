# Evidence-backed bounded release recovery

A failure/unknown notification should not remain apparently unresolved when a fresh
check returns healthy. ReleaseMonitor now sets `recovery: true` and `report: true`
once on failure/unknown → verified healthy. Initial health and repeated health do
not report; existing repeated failure/unknown suppression is unchanged. This is
caller-returned reporting intent, NOT email/alert delivery or a live scheduler.

The same SRE-validated ChartCheck and isolated investigation/browser adapter remain
in use. Freshness, scope, session, replay and explicit Stop guards run before
recovery classification. Unknown is never re-labelled healthy. Stop/end produce
no result, thus no recovery report. An expired session still stops the monitor;
there is no automatic reauthentication or restart.

## Executed evidence

`RELEASE_RECOVERY_DEMO.json` comes from a separately executed loopback HTTP scenario
using real Selenium waits with a fake DOM driver. Explicit synthetic navigation +
shortcut → issue → SRE validation → independent alternative route → failure
conclusion. Reuse the check with a 300-second caller-controlled cadence:

| Clock | State | Report | Recovery |
|---|---|---|---|
| 100 | healthy | false | false |
| 400 | failure | true | false |
| 700 | failure | false | false |
| 1000 | healthy | true | true |
| 1300 | healthy | false | false |
| 1600 | unknown/loading | true | false |
| 1900 | healthy | true | true |
| 2200 | healthy | false | false |
| 2500 | bounded end | no result | no result |

The source SHA256 and baseline are embedded in the actual output. No wall-clock
sleeps, public/private website access, model inference, recordings or deployment.
No ReleaseMonitor UI exists. Fresh affected-component screenshot gate remains
INCOMPLETE: related chart fixture not rendered; last verified local missing
libnspr4.so/remote Grid-to-separate-loopback routing blockers retained, not bypassed.
Output is not browser/model/full-product acceptance. No old screenshot substituted.

## Tests and reproduction

```
python -m unittest discover -s tests -v
cd ui && npm ci --include=dev --no-audit --no-fund && npm test && npm run build
cd ..
python evaluate.py
python -m examples.chart_release
```

Actual pre-fix regression: three failed report assertions (failure, loading and
transport error recovery). Final Python: 190 PASS, 5 opt-in actual-browser SKIP;
frontend 179 PASS; TypeScript/Vite build PASS (existing chunk-size advisory).
Evaluation: 60/60 diagnoses and 60/60 healthy counterexamples. Connected synthetic
UC1/UC2 example and separate HTTP scenario pass. Existing tests updated only where
healthy recovery intentionally now requests a report. No new dependencies/framework.

Compatibility: `recovery` is an additive boolean on each emitted tick result;
`report` now includes recovery. Consumers assuming every reported result is an
alarm must branch on `state`/`recovery`; no outbound transport was added. Dedupe
remains in-memory per monitor. Numeric health means only the validated chart
condition is satisfied, not that the incident or production release is resolved.
