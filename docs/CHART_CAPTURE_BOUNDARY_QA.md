# Fresh capture boundaries for SRE assistance and release checks

A new evidence ID does not make an older capture fresh. The existing 300-second
age limit admitted a bot capture at99 after the observed issue at100; it could
report healthy/failure even though it predated the observation it investigated.
Within shorter supported release cadences, a newly identified older capture also
could masquerade as recovery after a newer failure.

`ChartCheck.evaluate(..., captured_since=0)` now applies a capture lower bound
**after** existing scope/session/version/age/sample/value validation. Investigation
uses its source observation's capture time. A release starts at its start time
and advances its in-memory boundary only after a non-unknown, non-replayed result.
Rejected future/wrong-context/loading/replayed data cannot move the boundary.
Equal-second captures and old-but-still-valid underlying samples remain allowed;
this checks capture ordering, not strict sample progression or authenticity.

No new schema/dependency/framework/scheduler, live job, external notification or
browser recording. Existing explicitly validated check is shared by both uses.

## Executed evidence

- Three new regression methods initially produced six failed assertions, zero
  errors after fixing test setup (initial setup error is not product evidence).
- Full Python:205 run,200PASS,5 opt-in actual-browserSKIP,0FAIL.
- Frontend:179PASS;TypeScript/Vite buildPASS (existing chunk-size advisory).
-60/60 diagnosis pairs+60/60 healthy counterexamples; connected synthetic examplePASS.
- Fresh runnable scenario: `PYTHONPATH=.:tests python docs/chart_capture_boundary_demo.py`.
  Its actual output and source SHA-256 are in `CHART_CAPTURE_BOUNDARY_DEMO.json`.
  Real loopbackHTTP+Selenium waits/fakeDOM: consented navigation+shortcut→issue→SRE
  validation→independent alternative route rejects older capture/newID→fresh failure;
  SAME check→before-release unknown→healthy recovery→failure→rollback unknown (not
  recovery)→future rejection→valid equal-second recovery→failure/dedupe→loading
  unknown→recovery→bounded end. Uses a fake1s clock to expose within-age rollback;
  existing normal300s cadence coverage remains passing. No sleeps or live schedule.

## Evidence limitations / remaining gates

Fresh affected-component screenshot gate **INCOMPLETE**: this is a chart-check
API with no user-facing reporting UI. The related chart fixture was not freshly
rendered. Last verified local Chromium lacked`libnspr4.so`; remote Grid could not
reach the separately hosted loopback fixture. These unchanged blockers are carried
without repeated probes, sandbox bypass or old-image substitution. HTTP/fakeDOM
is not rendered-browser, real model, video, fullgraph or parallel acceptance.
Separate reviewer launch failed gateway1008/token mismatch; parent review only.
UC1/UC2 full agreed acceptance, expanded Studio and handoff remain open.

The watermark is local to one monitor instance, not durable scheduling state. It
cannot attest real capture provenance or catch forged timestamps/newIDs. Equality
is allowed at second resolution. No canonical owner DAG/workflows, deployed UI,
shared model, private recording,main release or production services were changed.
