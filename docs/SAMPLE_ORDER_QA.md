# Chart sample rollback — executed synthetic evidence

## Feature demonstration

Outcome: a newly captured chart must not turn older source data into a grounded conclusion or a release recovery.

Run `PYTHONPATH=.:tests python docs/sample_order_demo.py` from the repository root after installing `requirements.lock`.
Actual output is in `SAMPLE_ORDER_DEMO.json`; it includes the tested `triage/chart_checks.py` SHA-256. The runner uses a real loopback HTTP server and Selenium waits with fake DOM/WebDriver fixtures, **not a rendered browser, actual model inference or video**.

1. Consented synthetic navigation plus shortcut creates an issue; explicit SRE validation creates the shared ChartCheck.
2. A separate investigation follows the alternative entity route. A fresh capture with sample99 after observed sample100 returns unknown, not healthy/failure. Equal sample100 with fresh identity restores a grounded failure.
3. A bounded fast release (cadence1, caller-driven fake clock) observes failure sample100, then a newly captured healthy sample99. The second result is unknown, never recovery. Sample100 restores one recovery report; repeated healthy stays silent.
4. The SAME validated check runs the requested cadence300 bounded release: failure, duplicate failure, healthy recovery, loading unknown, recovery, end. No sleep, schedule installation or alert send.
5. Original observer events/URL remain unchanged.

## Scope and review

Four net production lines in the existing evaluator/consumers. `evaluate` adds a backward-compatible optional `sampled_since=0` keyword. Investigation compares with the final SRE sample; release retains its last validated, non-replayed sample timestamp. Unknown/loading/future/replayed reads cannot advance this watermark. A valid initial release sample may predate release start; equal sample timestamps remain legitimate (coarse sample clocks).

Two regression methods produced three failed assertions before the fix: independent false healthy, independent false failure and release false recovery. After the fix: 220 Python tests discovered, 215 passed, 5 opt-in actual-browser skips; 179 frontend tests passed; TypeScript/Vite build passed; evaluation 60/60 diagnoses and 60/60 healthy counterexamples; connected UC1/UC2 example passed. Compilation and whitespace checks passed. Existing Vite chunk-size advisory remains.

The cadence1 case is necessary to isolate sample rollback: at cadence300 the existing maximum300-second freshness condition normally already rejects a strictly older sample. This does not change cadence policy. Timestamp ordering is not authenticity; equal-timestamp value changes are permitted, clock accuracy is not verified and runtime state is not durable.

## Evidence limits / remaining gates

No UI genuinely exists for the changed chart evaluator/release API. The meaningful affected surface is the actual API adapter and runnable CLI demonstration above. Fresh rendered related-chart screenshot gate remains INCOMPLETE: historical local missing `libnspr4.so` and remote Grid-to-development-loopback restrictions are carried without repeating unchanged probes or bypassing isolation. No old screenshot is substituted.

Full UC1/UC2 actual-browser/model acceptance, expanded Studio full-graph/parallel execution/capture/replay and handoff remain OPEN. Existing author response is completed/finish-stop; live directory session status was `{}`. No stale snapshot was synced over owner changes; latest remote source was fetched into an isolated slice. Owner Studio sources/services/Grid/canonical files/recordings and main were not changed. Native separate-review delegation failed gateway1008 token mismatch; this is author review, not independent review.
