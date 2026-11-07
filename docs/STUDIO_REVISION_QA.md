# Saved-DAG revision for review-only generation

## Feature demonstration

Outcome: an editor still showing threshold 3 must not generate code for a same-ID task that another editor has already saved as threshold 9.

Run `PYTHONPATH=.:tests python docs/studio_revision_demo.py` from the repository root. [Executed output](STUDIO_REVISION_DEMO.json) records actual temporary loopback HTTP requests and hashes of the tested backend/UI source. A synthetic model double is used, not real Qwen inference.

1. Read canonical Python DAG at revision A (threshold 3).
2. Commit threshold 9 through the real revision-checked HTTP PUT, producing revision B.
3. POST generation with absent, stale A, wildcard or malformed `If-Match`: HTTP409, no candidate, **zero model calls**.
4. Reload B and POST: HTTP200, model double receives the canonical threshold 9, review pending/executed false.
5. Canonical Python bytes remain unchanged by all generation requests.

The existing during-generation revision recheck still discards a candidate if the DAG changes after inference starts. UI callback tests verify forwarding the loaded revision and showing reload/save instructions on409 without applying a candidate. TypeScript→real Python HTTP integration verifies stale rejection and reload recovery.

**Fresh affected-component screenshot gate INCOMPLETE:** the actual affected surface is Python inspector → Generate Python with LLM. Private Grid `/status` was ready, but a fresh synthetic smoke using the unchanged default native/sandbox-preserving Edge options failed with `SessionNotCreatedException`. No screenshot or rendered-control success is claimed; no `--no-sandbox`, container-isolation override, deployment or owner-service changes were used. API/callback evidence is not a substitute for a fresh rendered screenshot. No older screenshots substituted.

## Implementation and compatibility

- `triage/dag_server.py`: compare `If-Match` with the snapshot revision **before** generation lock acquisition/model access. Reuses existing409 convention; current in-flight recheck retained.
- `ui/src/App.tsx`: pass its existing loaded/committed revision into Python inspector.
- `ui/src/PythonInspector.tsx`: forward it as `If-Match`, not as model instructions. Existing409 error/reload guidance retained.
- `tests/test_test_integrations.py`: actual HTTP model-spy regression, missing/stale/empty/wildcard/malformed revision refusal, canonical recovery and unchanged bytes; existing valid generation requests now use a loaded revision.
- `ui/src/backend.test.js`: real TypeScript/Python HTTP generation and reload recovery.
- `ui/src/python-revision.test.tsx`: actual inspector callback with mocked hooks/fetch; not rendered-browser evidence.
- `docs/studio_revision_demo.py` / `STUDIO_REVISION_DEMO.json`: executable evidence and source hashes.

**API tightening:** generation clients must retain the revision from the DAG they loaded/saved and send `If-Match: <revision>`. Do not automatically fetch a new revision just before generating from an old displayed task: that defeats the user-visible context check. Missing revision now409 in test mode. Disabled mode still503. Existing optional alternate adapters may ignore the additional header.

Two net product lines; no helper, framework, schema, storage, scheduler or dependency. `If-Match` is an optimistic consistency boundary, not authentication. Unsaved local drafts are still drafts: save/review before generation. Single-process file ownership remains required. No generated code execution, no browser actions, no automatic retry/rebase/save, no real model eviction/reload or live chart schedule.

## Executed tests (2026-11-07 14:00 UTC)

- New regression before fix: one failed assertion, HTTP200 instead of409.
- `../demo/.venv/bin/python -m unittest discover -s tests -v`: **233 PASS /5 opt-in actual-browser SKIP (238 total)**, zero errors/failures.
- `npm ci --include=dev --no-audit --no-fund && npm test && npm run build` in `ui`: **183 frontend PASS**, TypeScript/Vite PASS; existing bundle-size advisory remains.
- `python evaluate.py`: **60/60 diagnoses +60/60 healthy**.
- `python -m examples.chart_release`: connected synthetic UC1/UC2 PASS.
- Demo above, compilation and staged whitespace validation PASS.
- Grid smoke: **BLOCKED**, SessionNotCreatedException; no sandbox fallback attempted.

## Acceptance boundaries

UC1 consented semantic navigation/shortcut → issue → explicit validation → separate alternative-route investigation remains green using HTTP/fake DOM; not real model-led SRE understanding. UC2 reuses that same observed check for caller-driven bounded300s release failure/dedupe/recovery/loadingunknown/end, with Stop/expiry/scope/freshness regressions retained. No production monitor.

Studio saved-context generation is improved; complete browser/model/recording/replay/fullgraph/parallel execution/handoff gates remain OPEN. Keep scheduled development enabled. No new actual browser/model/video acceptance, no owner deployment/service/canonical/recording modifications. Independent native reviewer launch was blocked by gateway1008/token mismatch; author review only.
