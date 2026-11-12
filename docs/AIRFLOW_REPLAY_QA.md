# Latest live verification — 2026-11-11

[Current run, exact-source discovery, terminal worker dependency failure, real pre-start cancellation and remaining merge gates](AIRFLOW_REPLAY_2026-11-11.md) supersede the historical connectivity details below. Final tests:287 passed/5 skipped Python,189 frontend passed,build passed. No successful Airflow browser run or fresh product screenshot is claimed.

## Historical November8 receipt

# Fast replay acceptance and remaining gates

This is a tested opt-in source slice, **not completed live Airflow handoff**. See [structured evidence](airflow-replay-evidence/acceptance.json), [clean real Selenium execution](airflow-replay-evidence/standalone-actual.json), [fresh real DOM scroll assertions](airflow-replay-evidence/new-source-scroll.json), and [authenticated app save](airflow-replay-evidence/app-save.json).

Executed: `python -m unittest discover -s tests` (284 pass, 5 opt-in browser skips), `npm --prefix ui test` (189 pass), `npm --prefix ui run build` (passed). Unit/fake Airflow HTTP and supervisor tests are not live scheduler/worker evidence. Standalone acceptance copied ONLY the exported `.py` into a clean temporary directory and ran workspace venv Python `-I` with stdlib + installed Selenium, explicit Grid origin and the existing selected container isolation. Six ordered steps/two clicks/two pages/final visible Errors: 0 passed; browser quit. No model configuration or project imports entered the child.

The real DOM scroll regression independently verified exact reported directional prose, scrollY0→1720, stable visible/reachable target, already-visible no movement, and rejection when covered. These screenshots show a regression fixture, NOT actual product controls. No fresh affected-control screenshot is claimed.

The authenticated Bun app returned401 without app credentials and201 saving the reviewed immutable artifact. Its normal fast-run HTTP route returned502 when Airflow became unreachable. Earlier authenticated live Airflow3.4.0 inventory had17 unrelated DAGs/no replay DAGs/no import errors. Subsequent direct connections failed `Operation not permitted`. Three versioned replay bundles were staged manual/paused/no catchup, but **discovery was not verified** and **no Airflow run ID/terminal worker or cancellation success exists**. Files in a mount are not migration proof. Original paths/workflows/recordings and unrelated DAGs/schedules remain unchanged.

Grid→isolated app timed out; no policy/sandbox workaround was made. Actual standalone Selenium and local authenticated app HTTP evidence do not establish browser-control→Airflow→browser→terminal UI acceptance. Missing/changed external fixture, actual Airflow stop/cleanup and broader actual negative scenarios remain gates. Existing default-off integration is safe to review without activating those runs.

Owner backend11490 and current live journey hash were verified, with owner public scroll run passed/idle. That runtime was not overwritten/restarted. This source ports target/completion guards and model choice narrowly into latest remote; it is not a full old deployed snapshot overlay. Production/private journeys, automatic monitors and emails remain unauthorized.

Final-runtime clean replay was rerun after review fixes. Additional actual Selenium fault-injected stale locator and wrong target artifacts failed visibly with cleanup; a reviewed replacement export passed with zero model calls. [Raw evidence](airflow-replay-evidence/standalone-negatives-actual.json). This does not claim an external fixture was mutated. The earlier real scroll geometry evidence predates later dispatch-boundary hardening; it proves the unchanged reveal behavior, not the final product-control gate.
