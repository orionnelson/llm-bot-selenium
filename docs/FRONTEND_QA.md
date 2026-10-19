# SRE frontend, recording and editable Python — QA

2026-10-19. This is a frontend/design slice; production services are not claimed.

## Executed locally

- `cd ui && npm test`: **63 passed**, including graph/connection round trips, HTTP-compatible IDs, event replay, configured numeric branch evaluation, custom-code execution refusal, recording pause/resume/stop/privacy/bounds, and actual Python AST parsing of frontend-generated artifacts.
- `cd ui && npm run build`: TypeScript + Vite **passed**. Optional lazy ELK bundle exceeds Vite's chunk-size advisory; primary frontend JS remains under500KB minified.
- Python regression suite with existing Selenium test dependencies: **85 tests run, 83 passed, 2 actual-browser tests skipped**. New `test_studio_python.py` covers config→Python, branch comparisons, syntax/contract validation, preserved edited code and no execution during export.
- Python compile checks for exporter and screenshot helper passed.
- Static host actual HTTP asset hashes checked against production build after deployment; existing Swiss application backed up. LAN URL owner-confirmed, not independently resolved from the OpenClaw pod.
- Optional generation endpoint without provider configuration: actual HTTP503 `status: pending`; no inference/credential access occurred.

## Not executed / blocked

- Real UI screenshot and pointer acceptance: local Chromium with default security fails `No usable sandbox`. Unprivileged namespace creation is blocked by the container. No sandbox-disabling flags were used. Alternate Firefox download sources timed out; downloader stopped.
- No screenshots were fabricated or checked in. `ui/scripts/capture_screenshots.py` is ready for a sandbox-capable development machine and captures only loopback fixture pages with an isolated profile.
- No actual LLM generation, real Selenium recording, webpage perception, external integration requests, production actions, scheduler, or Python runtime execution.
- Optional provider adapter authorization/timeout/response paths are implemented but no live provider was configured or called; needs deployment-specific integration testing before use.
- Existing GitHub Python CI is separate from the local frontend test/build evidence. This feature does not claim new frontend CI runs without a run receipt.

## Safety and persistence

- Generated/user Python remains source text. Reviewing it does not cause execution. Demo rejects custom Python rather than pretending it ran.
- Syntax validity is not a safety assessment. Exported modules may contain arbitrary user code; do not import/run unreviewed artifacts.
- Recording is explicitly UI-authoring metadata, not browser capture or a recording of typed content. No automatic upload or persistence of captures.
- LLM service token is component memory only; provider key is server environment only. Use HTTPS and real authentication/RBAC before public or sensitive deployment.
- Conditional configuration uses a restricted operator map, not JavaScript/Python eval.
