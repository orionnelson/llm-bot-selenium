# Exact integer chart conditions without float overflow

## Feature demonstration (fresh API execution)

Run `PYTHONPATH=.:tests python docs/chart_integer_demo.py` from repository root. [Fresh output](CHART_INTEGER_DEMO.json) records the tested source SHA-256 and latest remote base.

Consented synthetic navigation + shortcut → issue → explicit SRE validation → independent alternative-route investigation → SAME reusable bounded release check. Previously `math.isfinite` implicitly converted Python integers to floats: a valid `10**400` threshold/value crashed with OverflowError (or became unknown in a consumer). Now integer comparisons stay exact; only floats need a finiteness test.

Actual loopback HTTP/Selenium-waits/fake-DOM execution verifies a large explicit threshold, normal chart values, independent healthy conclusion and bounded release. Oversized DOM values STILL fail the existing 80-character text budget and produce unknown, then ordinary fresh evidence recovers. A separately labelled pure Python adapter verifies `10**400+1` is failure and exact equality recovers, without relaxing the browser adapter budget. The ordinary SAME observed check also executes cadence300 failure/dedupe/recovery/loading-unknown/recovery/end.

**Fresh related-component screenshot gate INCOMPLETE:** these Python numeric-validation APIs have no UI. Related chart fixture not freshly rendered; historical local missing libnspr4.so / remote Grid-to-development-loopback limitations carried, not reprobed or bypassed. No old screenshots substituted. No actual browser/model/video acceptance.

## Smallest fix and compatibility

Four existing guards test finiteness only for actual float values; Python integers are already finite. Zero net production lines, no helper/dependency/schema/framework/scheduler/permissions added. Negative integers (including huge negative integers), bools, NaN and infinities remain invalid; None is still missing data. Exact Python numeric comparisons avoid conversion/rounding. Browser payload/text limits and Python JSON parser limits remain unchanged. This does not promise JavaScript number precision, unlimited input size, unit calibration or evidence authenticity; no frontend numeric contract was changed. Other log-analysis and Studio numeric helpers are outside this chart-check change.

## Executed evidence

- Before fix: new regression methods reproduced **5 OverflowErrors**, zero assertion failures.
- Python suite: **232 PASS /5 opt-in actual-browser SKIP (237 total)**; zero failures/errors.
- Frontend: **179 PASS**, TypeScript/Vite build PASS; existing bundle-size advisory.
- Evaluation: **60/60 diagnoses +60/60 healthy**; connected synthetic UC1/UC2 example PASS.
- Fresh runnable demo, compilation and whitespace PASS.

No live monitor/alert, private recording, owner service/source/Grid/canonical changes, deployment or model reload. Monitor remains caller-driven, single-owner and in-memory; full browser/model/Studio/handoff acceptance remains open.
