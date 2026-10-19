# SRE frontend, recording and editable Python — QA

2026-10-19. This is a frontend/design slice; production services are not claimed.

## Executed locally

- `cd ui && npm test`: **95 passed**, including graph/connection round trips, HTTP-compatible IDs, event replay, configured numeric branch evaluation, custom-code execution refusal, recording pause/resume/stop/privacy/bounds, and actual Python AST parsing of frontend-generated artifacts.
- `cd ui && npm run build`: TypeScript + Vite **passed**. Vite reports chunk-size advisories for the approximately514KB frontend bundle and optional1.44MB lazy ELK bundle; real-browser performance acceptance remains pending.
- Python regression suite with existing Selenium test dependencies: **97 tests run, 95 passed, 2 actual-browser tests skipped**. New `test_studio_python.py` covers config→Python, branch comparisons, syntax/contract validation, preserved edited code and no execution during export.
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

## Control-flow / snippets / pane expansion — owner review hold

PR11 stays unmerged for owner review.

- **95 frontend tests pass**: structured for/while returns and caps, decreasing/empty ranges, scoped per-iteration IF/ELSE, invalid body paths, invalid Repeat destinations, pair deletion, distinct Python source forms, session clipping/source IDs/relative times, URL credential redaction, fragment removal, typed-value rejection, snippet persistence and Pending execution, old-layout migration and all pane dimensions.
- Three tests render the real React component markup server-side, including all five accessible splitter elements, loop editor fields and the honest no-session/snippet state. This is SSR evidence, not browser screenshots or pointer acceptance.
- Python regression: **97 run / 95 passed / 2 actual-browser skipped**. Frontend-generated for/while Python is additionally parsed by real Python AST in the frontend suite without executing source.
- TypeScript/Vite build passes, with chunk-size advisories (main about514KB, lazy ELK1.44MB).
- Live triage event transport, real browser playback, automatic webpage understanding and production execution are still pending. The live-buffer seam accepts manually imported event batches only.
- Loop simulation uses structured header/body/Continue/DONE blocks, at most100iterations per loop, four nested body levels and2500events total. It does not run arbitrary Python or allow arbitrary cyclic edges.
- Imports and reusable per-node snippets remain unverified plans; they never turn into fabricated browser success. Snippet metadata requires explicit data-boundary approval before an optional configured provider call.
