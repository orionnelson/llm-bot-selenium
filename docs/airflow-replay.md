# App-triggered deterministic Airflow replay

This integration is **off by default**. The normal DAG inspector, immediately
beside standalone Selenium export, provides review/consent, immutable save,
artifact selection, manual trigger, status/tasks/results, sanitized logs and stop.
It uses the canonical saved Python DAG and the existing strict standalone
exporter. Prompt-only tasks, arbitrary Python, branches, parallel graphs, loops,
custom source and incomplete/stale recordings are rejected by that exporter.

## Install and configure (server operator)

Use Airflow **3.4.x**, including its matching `apache-airflow-task-sdk`, and
`selenium==4.51.0` in the **task execution Python environment**. The SDK imports
are `from airflow.sdk import DAG, task, Variable, get_current_context`; legacy
Airflow 2 PythonOperator imports are not used. The app backend uses Python stdlib
HTTP and does not need an Airflow installation.

The operator supplies these environment variables to the Python app server:

| Variable | Meaning |
| --- | --- |
| `SRE_AIRFLOW_REPLAY_ENABLED=1` | Explicitly enable integration |
| `SRE_AIRFLOW_REGISTRY_DIR` | Private durable directory, shared by all app server instances; preserve across restarts |
| `SRE_AIRFLOW_DAG_DIR` | Existing writable, Airflow-watched DAG directory, e.g. the mounted `/airflow-dags` |
| `AIRFLOW_BASE_URL` | Server-only Airflow HTTP(S) origin, without credentials/path/query |
| `AIRFLOW_USERNAME`, `AIRFLOW_PASSWORD` | Server-only service account; alternatively use the injectable provider below |
| `SELENIUM_GRID_URL` | Operator-approved credential-free Grid origin embedded into the immutable bundle |
| `SRE_AIRFLOW_BROWSER` | `edge` (default) or `chrome` |
| `SELENIUM_ISOLATION_MODE` | `browser` (default native sandbox) or explicit `container` |
| `SRE_BROWSER_URLS` | Existing operator-approved synthetic URL JSON allowlist |

Isolation precedence is `SELENIUM_ISOLATION_MODE`, then `GRID_ISOLATION_MODE`, then
the existing `SELENIUM_GRID_ISOLATION`, then `browser`. Invalid modes fail closed.
Container mode explicitly requests `--no-sandbox` and the official Edge launcher
path, matching `triage/grid.py`. Browser mode checks the actual browser command
line and rejects disabled sandbox flags. There is no fallback between modes.
Changing Grid/browser/isolation requires reviewing and saving a new artifact;
old artifacts retain their exact original configuration.

Keep the existing loopback Python listener and authenticated `ui/serve-studio.ts`
Bun proxy. The proxy forwards only allowlisted routes after same-origin Basic
authentication. Browser Basic credentials are never forwarded to Airflow.
There is no client-supplied filesystem path, Python code, Grid origin, Airflow
origin, credential or run configuration field in this API.

### Credential provider / Vault

`AirflowClient(origin, credential_provider)` accepts a server callable returning
`(username, password)`. `from_env(credential_provider=provider)` builds the registry,
or construct `ReplayRegistry(root, dag_dir, client, config)` directly and inject
it with `triage.dag_server.handler(..., airflow_replay=registry)`.

The parent can wrap its externally installed `tools/airflow_vault.py` loader in
that callable. Adapt the loader's actual output to the tuple on the server;
no Vault import, secret file, credentials or secret values belong in this repo
or browser. The callable is invoked at token acquisition; JWTs remain in server
memory for at most 60 seconds before renewal. Authentication uses `POST
/auth/token`; API calls use `/api/v2` Bearer authentication. Redirects are rejected,
HTTP responses are capped at 1 MB and requests have a two-second transport timeout.
Exception/response bodies and provider errors are never returned to the browser.

The service account needs read access to owned DAG details/tasks/runs/task
instances/XComs, permission to trigger owned DAGs and change their pause state,
and create/update permission for its `sre_stop_...` Airflow Variables. Workers need
SDK Variable reads and XCom writes through the Airflow execution API. Cancellation
depends on these permissions; verify them in synthetic acceptance.

## Immutable lifecycle and manual scheduling

1. Save the canonical DAG normally. Choose complete current synthetic recordings
   in the standalone export controls when recorded replay is needed.
2. Review the serial steps, check **both** explicit review and synthetic consent,
   and save an immutable artifact. Requests use `If-Match` for the canonical
   revision. This deploys a complete portable `.py` DAG, with the entire standalone
   Selenium program and worker supervisor embedded. It does not run a browser.
3. Wait for Airflow's DAG processor to load it, select its hash ID and trigger.
   Trigger verifies the deployed bundle hash, loaded artifact tag and exact
   `replay_chain` task/retries contract. A missing/stale/unloaded DAG is an error.
4. Refresh until terminal to collect sanitized canonical task/step results and
   restore the owned DAG's paused state.

The hash binds standalone source, worker source, semantic spec, canonical
revision and server-selected browser/Grid/isolation. The deployed bundle also
has a checked exact byte hash. Files are published atomically without overwrites;
new immutable bundles never replace unrelated DAGs. The private registry allows
at most 100 saved artifacts. One task executes the whole serial chain with one
fresh Selenium session; canonical dependencies are preserved inside that task.
It has no triage imports, UI callbacks, backend callbacks, model calls or repairs.
Run `conf` is always `{}` and is never read by the worker.

Each generated DAG has `schedule=None`, `catchup=False`,
`is_paused_upon_creation=True`, `max_active_runs=1`, `max_active_tasks=1`; its task
has `retries=0`. A paused manually triggered run can stay queued, so the app
temporarily unpauses **only the selected hash-named DAG** before submission and
re-pauses it on terminal status reconciliation. It never changes unrelated DAGs.
If the app is closed, the DAG remains schedule-less; reopen and refresh its run
to reconcile and re-pause. An API error is not reported as successful scheduling.

`flock` plus an fsynced active-run journal serializes app operations and survives
restarts. An Airflow query additionally rejects queued/running runs for the selected
DAG. Keep one durable registry for this integration; do not clear or replace it to
recover an ambiguous trigger. The run ID is written **before** unpause/submission,
so a lost POST response cannot silently create another run. Refresh reconciles that
same ID. If failure occurred before Airflow accepted submission and its run remains
404, the active journal intentionally blocks further triggers. An operator must
check that exact run ID in Airflow, re-pause this owned DAG and resolve/archive
that journal before retrying. Ordinary replay never reloads the editable DAG.

## Honest stop and structured evidence

Stop writes Airflow cancellation Variables scoped to the exact artifact/run.
A permanent pre-start marker prevents a queued run from creating a browser even
if scheduled much later. Minute-bucket markers bound negative Variable-cache
latency for a running worker; allow about **80 seconds** for observation and
cleanup under a healthy execution API. Variables are delivered through Airflow's
supported public API and read with its SDK, not through application callbacks.

The worker supervisor SIGTERMs the bounded standalone subprocess. The runtime's
signal handler reaches `finally: driver.quit()`. The supervisor allows 15 seconds
of cleanup before SIGKILL, and also handles Airflow termination signals in its
own `finally`. The subprocess has a 330-second supervisor ceiling; the Airflow
task has a 370-second execution timeout. Grid transport calls use bounded
timeouts. Configure the operator's normal Grid idle-session timeout for transport
loss or an unresponsive Grid where `quit()` itself cannot complete.

The app shows **stopping**, not cancelled, until Airflow reports terminal state.
An intentionally stopped task reports `failed` in Airflow and retains
`stopRequested` in app status. There is no patch-task-state cancellation. If the
execution API/scheduler is unavailable, status remains unresolved and the durable
active record continues to prevent another app run.

The runtime emits bounded `REPLAY_RESULT` JSON for each canonical task/step.
The supervisor emits `REPLAY_SUMMARY` and writes `replay_result` XCom before
raising on failure. Failed steps identify canonical task and step. App logs are
derived only from sanitized structured XCom events; raw worker/provider/DOM/Grid
logs and exception bodies are never forwarded. Results are available after task
completion; a crashed worker may have no XCom, while Airflow's terminal failure
is still shown. Model-assisted repair remains the existing separate opt-in,
reviewed workflow and always requires a newly reviewed artifact.

## App API (same-origin authenticated proxy)

All routes start with `/api/airflow/artifacts`:

| Method / suffix | Body / response |
| --- | --- |
| `GET` | Configured flag, public saved artifacts, active journal |
| `POST` | `{"runIds":[],"reviewed":true,"synthetic":true}` plus saved `If-Match`; immutable artifact metadata |
| `POST /{hash}/run` | `{"confirmed":true}`; exact immutable run ID/state |
| `GET /{hash}/status` | Airflow run state, task instances, sanitized canonical step results |
| `GET /{hash}/tasks` | Same status envelope, including task instances |
| `GET /{hash}/logs` | Sanitized structured event lines; no raw logs |
| `POST /{hash}/stop` | `{"confirmed":true}`; stopping/request state |

POST bodies are capped at 8 KiB and exact schemas reject extra fields. Disabled
integration returns 503. Invalid consent/revision/active-run/loaded-artifact
contracts return 409; Airflow failures return sanitized 502 without claiming
success. Saved artifacts expose only hash, revision, ordered task IDs and time.

## Verification and rollback

These commands are for the parent to execute; this source-only change does not
claim unit, build or live acceptance results:

```text
python -m unittest discover -s tests -p 'test_airflow_replay.py' -v
python -m unittest discover -s tests -p 'test_standalone.py' -v
python -m unittest discover -s tests -p 'test_dag_server.py' -v
npm --prefix ui test
npm --prefix ui run build
```

`test_airflow_replay.py` uses a fake HTTP transport and stdlib subprocess double;
it is not evidence of an Airflow run or Selenium session. Parent acceptance must
use the reviewed synthetic fixture, confirm SDK/API compatibility and loaded
bundle, inspect genuine Selenium task/step results, stop a live task, verify Grid
session cleanup and terminal reconciliation, and retry across an app restart to
check duplicate suppression. Verify paused/manual behavior on the target
Airflow 3.4 installation. No deployment, Vault or cluster tools are changed here.

For rollback, stop and reconcile the active run first, then remove
`SRE_AIRFLOW_REPLAY_ENABLED=1` and restart the app. Preserve the private registry
for audit/recovery. Operator archival may remove **only** inactive
`sre_replay_{hash}.py` bundles and their corresponding saved registry/last-run
records, and expired `sre_stop_{hash}_{runId}_...` Variables after terminal runs.
No automatic cleanup touches any unrelated DAG, Variable or run.


### Airflow 3.4 handoff and postconditions
The server verifies the **loaded** `/dagSources` SHA-256 against the immutable deployed bundle before triggering. `drain_dag=true` executes the explicitly requested manual run and lets Airflow restore paused state even if the app disconnects. Only this owned schedule=None DAG is drained; no unrelated schedule is modified. Status also confirms/reasserts paused on terminal observation.

A same-page click requires an explicit next visible-result assertion. The runtime refuses an already-satisfied effect without clicking, dispatches at most once, and verifies the effect before recording the click passed. A no-op cannot advance to the next action. Navigation clicks require the expected approved destination and locator/tag/href identity. Known fixed failure reasons are displayed; arbitrary worker text is never forwarded.

This release is a serial, annotated synthetic replay subset, not a promise that old prompt-only/public recordings can be migrated. Unsupported operations, contexts and control flow fail export explicitly. Existing owner runtime/retry/storage patches are not overwritten by this isolated source; deployment of a complete old snapshot is not a handoff procedure.
