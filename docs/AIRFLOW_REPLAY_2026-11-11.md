# Live synthetic replay verification — 2026-11-11

## Feature demonstration and remaining gates

The real authenticated app submitted manual Airflow run `replay__469c47da93cb4327b27275128b8e19f5` for artifact `e69ea99a94d04b821e1c6afd55ffba131fe3a39acae5f7580a46dda00312d8b8`. Live discovery verified the exact loaded/mounted source SHA-256 `7f29ff32e692d75f1ee75160309170aaa9a0972cdab97d6859c80dbc431cc9bf`, no import errors, manual/paused policy and the single ordered-session task `replay_chain` with zero retries. The app returned HTTP202, then actual terminal **failed**, task failed/try1. Its worker summary contained no step events. The DAG was paused afterward. [Structured terminal evidence](airflow-replay-evidence/2026-11-11-live-terminal-failure.json).

This is real app→Airflow→worker→app **failure-path** evidence, not successful browser replay or handoff. The child exited before its first browser event. A missing worker Selenium installation is a hypothesis until a diagnostic run establishes it; do not infer a specific dependency failure from an empty result.

The new source preserves a fixed, credential-free startup diagnostic when Selenium is missing, and the worker reports an allowlisted startup failure if a child exits without step events. Raw stderr, environment, provider logs and paths are not forwarded to the browser. A real isolated Python `-I -S` subprocess reproduces missing Selenium; it now emits the structured failure instead of only generic stderr. No dependency installation, worker image change or permissions change is performed.

**Current-version live result:** artifact `c8c51c5bff3fd18d249986b245bd34256e7c5787f48d398930817c46c3114825` was actually discovered with matching source, no import errors and paused/manual policy. Authenticated app run `replay__41d60960af9348118e3c61a3ad6bc9c2` reached terminal failed/try1. The real child reported **`Selenium dependency unavailable in replay environment`** through worker XCom and the app's sanitized logs. The DAG re-paused. This establishes the dependency blocker, not successful Airflow browser execution. [Actual final-source receipt](airflow-replay-evidence/2026-11-11-live-acceptance.json). Discovery required waiting for the parser's file refresh; earlier404s were not treated as success. Each replacement is a new immutable artifact; earlier files are retained, not overwritten.

**Operator prerequisite:** install the documented Selenium dependency in the actual Airflow worker image/environment used by `sys.executable`, through the normal worker-image deployment process. Installing it only in the gateway venv or mounting a script does not fix the worker. Do not add network package installation to ordinary fast replay, change unrelated workers/schedules, or claim the environment repaired from a local install. Successful live browser replay must be rerun afterward.

**Fresh affected-control capture is blocked:** actual Edge155 Grid navigation to the isolated authenticated Studio timed out. The owned session was quit. No policy/sandbox fallback, auth removal or older screenshot substitution was used. This remains a merge/handoff blocker, as does successful live browser execution and running-browser cancellation/cleanup verification.

**Actual pre-start cancellation passed:** authenticated app run `replay__bda9b82c3cd248b28e1ce614be99f866` accepted Stop (HTTP202/stopping), then the real worker rejected startup with `Synthetic replay stopped before browser startup`, pushed XCom `state: stopped`, and reached Airflow terminal failed/paused. [Stop receipt](airflow-replay-evidence/2026-11-11-live-stop.json). Airflow failed is the expected terminal representation here, not success. This proves the queued/pre-start marker path, NOT termination or cleanup of an already-running browser.

## Actual tests on the final local source

- Python: 287 passed, 5 opt-in browser skipped, 292 total; zero failures.
- Frontend: 189 passed; TypeScript/Vite build passed, existing large-chunk advisory.
- New missing-dependency regression reproduced one assertion failure before the fix.
- Unit worker-crash/XCom/app-log tests verify structured failure without exposing injected secret stderr. These are not real worker success evidence.
- Actual clean-directory exported Selenium replay: six ordered steps, two clicks, two pages, final visible `Errors: 0`, session quit; zero model calls or project imports. [Final-runtime receipt](airflow-replay-evidence/standalone-actual.json).
- Actual fault-injected stale locator and wrong-target artifacts fail visibly; reviewed replacement passes. [Receipts](airflow-replay-evidence/standalone-negatives-actual.json). This does not claim the external fixture itself was mutated.

## Source coordination and scope

The old owner implementation process is failed/finished and both OpenCode author directories report idle. No duplicate author was started. The public `blue-master` remains `342a9c6552208b005a31d0f725f8f45f3e16f6dc`; PR61 was open at `75ad93d7fd8fe15c873c0d340638d27bb232d81a` with both exact-head checks green before this update. Local inspection found completed but unpublished safety-review follow-ups (dispatch identity/private-boundary, input retention, pre-start cancellation, review-consent invalidation). They are preserved and tested with this coherent replay update rather than overwritten with the older published head.

Existing Email/Allenfort and completed-scroll correctness changes and Qwen3.6 Q4 no-think selection remain. No model reload/inference, production/private journey, owner runtime restart, unrelated DAG/schedule modification or main release occurred. The temporary authenticated acceptance app uses isolated state. Native independent-review delegation remains blocked by gateway token mismatch; existing separate source review is not relabeled as independent visual approval.

UC1/UC2 synthetic regressions remain covered by the suite. No new actual model/SRE/release-monitor acceptance or complete Studio handoff is asserted. Keep development enabled. Next major-feature step: establish the final artifact's live discovery and worker dependency/runtime prerequisites, then complete successful app→Airflow→browser→app, real stop/cleanup and fresh affected-component captures.
