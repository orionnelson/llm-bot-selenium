# Standalone Selenium export

The normal **Export standalone Selenium .py** control is available in the DAG
inspector and recorded browser-run panel. It downloads one Python file containing
the complete fixed runtime and an embedded JSON specification. The UI never runs
it. The older **Export inert Python DAG definition** remains a repository-dependent,
review-only constructor definition; it is not Selenium replay.

## Prepare and export

Export reads the **canonical saved DAG**, not a client-submitted definition. Save
first. Configure `SRE_BROWSER_URLS` on the local editor server to a JSON array of
exact approved synthetic fixture HTTP(S) URLs (at most ten). Default fixture URLs
remain `http://127.0.0.1:8080/` and `/details.html` on that origin. Grid must be able
to reach the fixture; its loopback is usually not the editor machine's loopback.

Two sources can be used, including different sources for different serial tasks:

* **Recorded:** in the browser policy editor, explicitly approve the fixture URL,
  action IDs and expected text as synthetic standalone metadata; save and reload
  the policy, then consent to a new annotated browser run. This saves
  `params.replay_capture = {"synthetic": true}` and sets retries to zero. A passed
  run now includes verified initial navigation, per-click stable ID/tag/href,
  URL assertions, explicit ready-region waits and final result assertion. Choose
  one completed run per task in the DAG panel, or export the selected recording
  from its browser panel. Multi-task exports need every task represented. The
  browser panel's single-run export will reject missing other tasks; use the DAG
  panel to select the complete set.
* **Reviewed explicit data:** author `Task.params.replay` as below in the saved
  DAG. Use canonical action `application` (UI-compatible), zero retries, empty
  Python implementation or the exact unedited generated starter. These steps
  are the task's explicit replay meaning, not inferred from its prompt.

```json
{
  "version": "sre-replay-task/v1",
  "synthetic": true,
  "steps": [
    {"op":"navigate", "pre_url":"http://fixture:8080/", "post_url":"http://fixture:8080/", "url":"http://fixture:8080/", "wait":{"kind":"ready_region","timeout":10}},
    {"op":"click", "pre_url":"http://fixture:8080/", "post_url":"http://fixture:8080/details.html", "id":"open-details", "tag":"a", "href":"http://fixture:8080/details.html", "wait":{"kind":"ready_region","timeout":10}},
    {"op":"assert_text", "pre_url":"http://fixture:8080/details.html", "post_url":"http://fixture:8080/details.html", "id":"status", "text":"Synthetic replay complete", "wait":{"kind":"ready_region","timeout":10}}
  ]
}
```

`python -m triage.standalone_demo` contains a complete two-task, two-page example
builder. Only navigation requires a `url`; only clicks require `tag` and `href`
(`null` for a button); result operations require `id` and `text`. Every operation
requires `pre_url`, `post_url`, and the exact explicit wait shown above. URL
assertions must be continuous across tasks. Recordings made in separate sessions
with incompatible URL boundaries are rejected rather than spliced speculatively.

HTTP: `POST /api/dag/export/selenium`, same-origin JSON body
`{"runIds":["<opaque completed run id>"]}`, header `If-Match: <saved revision>`.
An empty list exports explicit saved data. The endpoint shares the loopback/Host/
Origin boundary, disallows transfer encoding, bounds the request to 8192 bytes,
and rechecks revision before returning a bounded attachment. Invalid evidence is
a visible 422, stale revision a 409. Client paths, source and allowlists are never
accepted. Recorded export needs the existing test-mode recording store; explicit
data export also works without test mode. No model call or browser session occurs
during export. No DAG or recording is modified.

CLI (run from the repository during export only):

```text
python -m triage.standalone workflow_dag.py --revision <sha256-of-saved-file> --urls approved-urls.json --run completed-manifest.json --output workflow_standalone.py
```

Omit `--run` for explicit data, repeat it for distinct tasks. Inputs are bounded
to 1 MB each. The revision is the SHA256 of the exact input bytes (also supplied
by `GET /api/dag` for its canonical Python file). Output is exclusive-create:
reviewed regeneration needs a new filename.

## Run outside this repository

Install Selenium in the chosen interpreter/virtual environment, not just its user
site (`-I` disables user-site packages). The project already lists Selenium; no
new package is introduced. Copy **only** the downloaded `.py` to a clean
directory, or another machine with Python and Selenium. No `triage`, backend, UI,
model, recording directory, prompt or PYTHONPATH is needed.

```text
python -m pip install selenium
python -I workflow_standalone.py --check
python -I workflow_standalone.py --grid http://selenium:4444 --browser edge
python -I workflow_standalone.py --grid http://selenium:4444 --browser chrome
```

The Grid origin must be provided by `--grid` or `SELENIUM_GRID_URL`; Edge is the
explicit default browser. There is no local-browser or alternate-endpoint
fallback. Each invocation requests a fresh headless session, requests no existing
profile and no sandbox-disabling flags, verifies the browser command line via
CDP, and fails closed if that verification is unavailable or sandbox-disabling
switches are found. A Grid configured with `--no-sandbox` will fail; the editor's
separate container-isolation option does not relax standalone replay.

Exit 0 with `PASS` means all fixed operations and the final visible result
assertion completed in that invocation. `--check` is data validation only, never
browser evidence. Exit 2 reports a synthetic task/step ID and sanitized reason,
without raw transport/DOM errors, environment values or screenshots. Startup,
failure, cancellation and success all attempt `quit()`. SIGINT/SIGTERM stop further
actions and clean up. Grid transport, page-load, script and wait timeouts are ten
seconds; implicit waits are zero. Canonical task timeouts are retained, capped at
the stricter 300-second run ceiling. Limits: 100 tasks/actions, 300 seconds per run,
plus a 20-second hard transport/cleanup grace ceiling. A nonresponsive Grid can
prevent confirmed remote cleanup; its infrastructure must expire abandoned
sessions. The hard process ceiling does not falsely report successful cleanup.

## Safety and supported semantics

Supported fixed operations are `navigate`, `click`, `input`, `wait_visible` and
`assert_text`. No generated Python, arbitrary JavaScript, arbitrary CSS/XPath,
keystrokes, shell commands or semantic shortcut injection is accepted. Start/End
are checked structural boundaries; their ordinary default UI metadata is inert.
The exporter follows the sole explicit serial `next` chain, checks its declared
dependencies, rejects disconnected items, and contracts structural Start/End
around the ordered replay task chain. Storage order never determines execution.

Controls must have unique stable `data-sre-action="id"` and
`data-sre-safe="true"`, inside the one visible `[data-sre-observe]` region. Links
must retain the exact approved absolute href and tag. Buttons must explicitly
be `type="button"`. Disabled/ambiguous/changed controls fail. Results use unique
`data-sre-result="id"` and exact visible synthetic text. Private, editable,
password and form boundaries (including form-associated controls) are forbidden;
result text is not read if it includes private/form/input descendants. The runtime
reads no region text, page source, screenshots, model evidence or field values.

`input` is non-sensitive synthetic filtering only: a text input outside forms,
annotated `data-sre-action`, `data-sre-safe="true"`,
`data-sre-input="synthetic"`, and `autocomplete="off"`, without sensitive field
metadata. Specify `env: "SRE_REPLAY_INPUT_FILTER"` instead of a literal value.
Only explicitly named `SRE_REPLAY_INPUT_*` refs in the artifact are read. Values
are bounded to 80 simple synthetic characters and are never logged or embedded.
This feature does not support password, secret, personal-data entry or submit.
Do not use real secrets as synthetic input. Secrets have no literal export path.

HTTP(S) URLs must be exact operator-approved entries, with no credentials, query,
fragment, encoded paths or sensitive path names. The artifact's URL list is
narrowed to URLs actually referenced by its verified steps. Current top-level URLs are
checked before/after actions and throughout waits; the initial fresh blank page
is the sole startup exception. Redirect escapes fail visibly. This is not a
replacement for fixture/Grid network egress isolation: the runtime does not
intercept subresource traffic or undo a navigation already attempted by a page.
Use consenting synthetic fixtures on operator-controlled infrastructure only.

Unsupported at **export time**: branches, loops, parallel paths, snippets,
custom-source tasks, unknown action names, prompt-only intent, missing locator/
URL/wait evidence, incomplete/unverified runs, mismatched policies, duplicate
run choices, stale revisions, missing final assertions and frame/window-context
operations. No frame or window switch can be expressed; unexpected extra windows
or non-top context fail at runtime. Current public journeys and legacy recordings
lack approved stable synthetic trace metadata and are explicitly rejected with
recapture guidance. Nothing is silently skipped or guessed.

The canonical DAG remains the review/self-healing layer. Replay is deterministic
and has **no** self-healing or model dependency. A changed fixture should fail.
Review the new evidence/locator in the canonical workflow, recapture if needed,
and create a separate new export. Never repair the old artifact in place.

## Evidence commands (parent/operator runs these)

Unit/contract checks, including WebDriver **doubles**, are not real browser proof:

```text
python -m unittest discover -s tests -p test_standalone.py
python -m unittest discover -s tests -p test_dag_server.py
python -m unittest discover -s tests -p test_browser_loop.py
python -m unittest discover -s tests -p test_journey.py
npm --prefix ui test
npm --prefix ui run build
```

For opt-in **REAL** evidence, provision a sandbox-enabled Edge/Chrome Grid and an
external synthetic fixture reachable from it. The supplied fixture is an optional
separate named server; create `/tmp/replay-variant.txt` with `show-result` using
your editor, then on the fixture host:

```text
python examples/standalone_fixture.py --bind 0.0.0.0 --port 8080 --variant-file /tmp/replay-variant.txt
```

Run on the client with Selenium installed:

```text
python -m triage.standalone_demo --consent-synthetic-clicks --grid http://selenium:4444 --home http://fixture:8080/ --details http://fixture:8080/details.html --browser edge --reviewed-new-id show-result-v2
```

The runner executes the baseline artifact in a temporary directory containing
**only that file**, with `python -I`, clean HOME/env and no PYTHONPATH. It requires
two real clicks across pages and the final assertion. At the first prompt, edit
the external variant file to `show-result-v2`; the **identical original artifact**
must fail at the missing control, with no model. At the second prompt, explicitly
confirm locator review; a separate regenerated artifact must pass in another
clean child process. Each child uses a fresh session and attempts cleanup. Only
then does the runner print a REAL evidence summary and distinct artifact hashes.
Grid/startup failure is a failure, never a silent skip or an accepted missing-
element test. Nothing here claims those real runs occurred during implementation.
