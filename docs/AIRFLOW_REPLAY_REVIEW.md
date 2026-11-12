# Independent source review, not visual acceptance

Distinct local-agent process, session cb524971-cc05-429c-aea0-404e367de634. No code/deployment executed by reviewer.

What this change does: Saves hash-bound synthetic Selenium workflows as portable Airflow DAGs, with duplicate suppression, structured results and cooperative stop. Reviewed statically for a shared durable registry; no tests or application code executed.

## Must fix

1. **P1 — Journey can click an excluded form control** (`triage/journey.py:28–31,281–295`)
   - **What this is:** Candidate IDs come from page-controlled attributes; dispatch uses the first matching element.
   - **Problem:** Put a visible form-submit button before a safe News link, both carrying the same `data-journey-candidate`. Observation excludes the form button, but `find_element()` selects it. Dispatch checks visibility/enabled state, not its actual identity or form boundary, and submits it.
   - **Fix:** Require exactly one matching element and revalidate its label/tag/href and private/form boundary immediately before dispatch. Add this duplicate-ID regression test.
   - **If skipped:** An untrusted public page can substitute a write action for an approved read-only click.

2. **P2 — Early termination can launch a child without terminating it gracefully** (`triage/airflow_worker.py:27–31,46–74`)
   - **What this is:** Signal handling records `stopping` and terminates an already-assigned subprocess.
   - **Problem:** SIGTERM before `process` is assigned sets the flag but execution still reaches `Popen()`. The loop then waits 15 seconds without sending SIGTERM to that child, finally killing it without browser cleanup.
   - **Fix:** Abort startup when already stopping; after process assignment, forward any pending termination before waiting. Test a signal during the pre-start Variable read.
   - **If skipped:** Stopping the Airflow task can start browser work after cancellation and leave its Grid session behind.

3. **P2 — Input no-ops can report success** (`triage/standalone_runtime.py:241–255`)
   - **What this is:** Input steps clear/type, then verify only page readiness and URL.
   - **Problem:** A readonly synthetic text field—or an input handler that discards keystrokes—can accept the WebDriver commands without retaining the value. A pre-existing final result then lets the replay pass. Existing input tests check dispatched commands, not their effect.
   - **Fix:** Verify the approved synthetic input’s retained value without logging it, or require a fresh, explicit visible effect before marking input passed.
   - **If skipped:** Airflow can report successful replay although the requested filter was never applied.

4. **P2 — Review consent survives snapshot changes** (`ui/src/AirflowReplay.tsx:13–20,27–29`)
   - **What this is:** Review and synthetic approval are persistent checkbox booleans.
   - **Problem:** Check both boxes, then change/save the workflow or change selected recordings. The approvals remain checked; `save()` fetches the latest revision and accepts the changed snapshot without renewed review.
   - **Fix:** Bind approval to the reviewed workflow/revision and recording selection; invalidate it when either changes. Add an interaction test.
   - **If skipped:** Immutable artifacts can accurately preserve content that was not the content approved.

**Verdict: fix 1–4 first.**

**Not checked:** Runtime/API compatibility or visual acceptance. Product Grid-to-isolated-app capture remains blocked by navigation timeout; synthetic screenshots are not product UI evidence. No edits or deployment performed.

## Parent resolution (not independent re-approval)
All four findings addressed: unique locator and actual DOM label/tag/href/private/form checks repeated after reveal; stop flag checked before subprocess startup and forwarded immediately after assignment; synthetic input retained value verified without logging; UI approval tied to exact workflow/recording selection and fetched revision, invalidated when changed. Focused negative regressions added. Final tests/build rerun. Product screenshots/live Airflow remain blocked.
