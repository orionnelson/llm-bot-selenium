# Python-first functional DAG definitions

## Existing Python foundation

The implementation uses **Python's existing `dataclasses` and `graphlib.TopologicalSorter`**, not a hand-written topological-sort algorithm or a new scheduler dependency. The repository already uses dataclasses for its core contracts.

Sources consulted:
- https://docs.python.org/3/library/dataclasses.html
- https://docs.python.org/3/library/graphlib.html

These standard-library structures fit the current scope: itemized functionality, explicit dependencies, validation and static plans. Installing/deploying Airflow, Prefect or a workflow service solely to represent a graph would add operational machinery without connecting a real executor. **This is not an Airflow-compatible DAG or a production scheduler.** It is a typed, validated Python definition ready for an approved future execution adapter.

## One task item per canvas item

`triage/dag.py` provides:

- `DAG`: functional definition and scope-aware graphlib validation/plans.
- `Task`: stable ID, action, kind, explicit predecessors, named output routes, parameters, predicate, scope, error policy and implementation.
- `LoopSpec`: for/while bounds, step, cap, BODY entry, Continue boundary and body-task IDs.
- `PythonSource`: source/origin/review metadata stored as **inert text**, never inserted as executable module-level user code.

The UI's **Task DAG** inspector displays the selected item as a Python constructor. The canvas **DAG** button shows the whole Python definition. Primary `.py` export is now an actual itemized `DAG(...)`, not a disconnected list of functions. Existing per-node Python editing remains available in the Python tab.

Example (no actions run):

```python
from triage.dag import DAG, Task, PythonSource

dag = DAG(
    name="Numeric branch",
    tasks=(
        Task(
            task_id="check",
            label="if i > 3",
            action="condition",
            kind="branch",
            routes={"yes": "high", "no": "low"},
            predicate={"input": "i", "operator": ">", "threshold": 3, "sample": 5},
        ),
        Task(task_id="high", label="High path", action="end", kind="end", depends_on=("check",)),
        Task(task_id="low", label="Low path", action="end", kind="end", depends_on=("check",)),
    ),
)
dag.validate()
print(dag.plan())  # static structure only; does not run either branch
```

A static topological plan lists possible tasks; it is **not** an execution schedule that blindly runs both branches. Named routes retain conditional semantics for the execution adapter. The frontend's explicitly labelled deterministic demo continues to evaluate selected branches and bounded loop bodies; neither planner nor demo executes edited Python.

## Loops without breaking the DAG

A loop header is a compound task. Its direct body members have `scope="loop-id"`; nested loops have their own scopes. Root and each body scope are independently acyclic and checked by `TopologicalSorter`.

The visual dashed Continue→Repeat line is **control metadata**, not a dependency back-edge. `LoopSpec` keeps the Continue ID and body entry explicitly. `dag.plan()` returns root order and each body's order. This avoids passing a cyclic graph to a DAG framework or silently treating a while loop as a one-shot action.

Validation rejects duplicate/missing IDs, dependency cycles, scope cycles, cross-scope routes, inconsistent dependencies, invalid ports, incomplete IF/ELSE, orphan Continue boundaries, malformed loop paths and invalid caps. Python-source review status is not a security attestation.

## Functionality separate from JSON layout

- **`workflow_dag.py`**: canonical Python functional definition; no positions, zoom, colors or panel sizes.
- **`workflow.layout.json`**: `sre-layout/v1` visual node positions, keyed by stable task ID. Pane dimensions remain per-user local UI state.
- **DAG JSON / bundle**: typed `sre-dag/v1` transport representation of the same Python model; bundles pair it with separate layout. This is not a separate execution language.
- **Legacy template JSON**: retained for editable drafts, compatibility and unused template/snippet library assets. It is not executed. Save also writes a separate functional Python artifact and layout artifact when wiring is complete; incomplete drafts are preserved without overwriting the previous valid Python definition.

Import accepts typed DAG specs, DAG/layout bundles, separate layout JSON and old visual templates. A layout import only changes positions. Per-node snippet snapshots remain functional task parameters; unused palette/library templates stay in template JSON.

## CLI and safe round trip

From the repository root, Python3.11+:

```sh
# Existing visual template -> Python DAG + separate JSON layout
python -m triage.dag workflow.json --output workflow_dag.py --layout workflow.layout.json

# Hand-edited Python definition -> validated transport for UI Import
python -m triage.dag workflow_dag.py --format spec --output workflow.dag.json

# Validate and inspect root/body orders, without running anything
python -m triage.dag workflow_dag.py --format plan

# DAG transport -> Python definition
python -m triage.dag workflow.dag.json --output workflow_dag.py
```

The safe `.py` loader uses Python **AST** with an allowlist: literal values and keyword-only `DAG`, `Task`, `LoopSpec`, `PythonSource` constructors; the known import declaration; `dag = ...`; and `dag.validate()`. Submitted imports, arbitrary calls, comprehensions, attribute access, expansions and executable statements are rejected. It never uses `eval`, `exec` or imports submitted code. Handler strings are preserved, not run. This restricted declarative format intentionally does not accept arbitrary Airflow-style Python builder scripts.

The earlier `triage.studio_python` exporter remains as a compatibility helper for review-only handler files; `triage.dag` and the UI's primary Py/DAG exports are the functional DAG interface.

## UI defects fixed with this change

- The top-right tab strip occupies a shrinkable, horizontally scrollable grid column; the DEMO/REPLAY badge and maximize button have their own reserved columns. Triage cannot render beneath the badge.
- React Flow is explicitly positioned against all four edges of a full-width, stretchable canvas. The center grid track uses `minmax(0,1fr)` so it does not leave a stale minimum-width gap or overflow its right boundary when panes resize.
- These are structural CSS/SSR regression checks, **not pixel or pointer acceptance**. Actual screenshots remain blocked by the runtime's missing usable browser sandbox; no browser security is disabled.

## Executed evidence and boundaries

-95 frontend tests pass, including full Python-definition load/roundtrip through the real dataclass loader/graphlib planner, scope and layout separation, branch preservation and header/canvas CSS contracts.
-97 Python tests run:95passed,2actual-browser skipped. Nine DAG tests cover real graphlib ordering, Python/spec roundtrip, inert hostile handler text, rejected executable Python, cycles, scope/Continue rules and layout independence.
-TypeScript/Vite production build passes (bundle-size advisories remain).
-No production execution, scheduler, live session capture, credentials or model inference is enabled by this implementation. Graph validation and source review are not a Python execution sandbox.
