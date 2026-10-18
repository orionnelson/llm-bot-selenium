# Milestone 04 — 2026-10-17

## Actual executions (local OpenClaw workspace)

- `.venv/bin/python -m unittest discover -s tests -v` — exit 0; **52 tests discovered, 51 passed, 1 skipped**. Skipped test is real Chrome/Selenium integration, explicitly NOT RUN.
- `.venv/bin/python evaluate.py` — exit 0; 60 deterministic cold/learned scenario pairs across 3 fixture failure classes, 5 catalog-order seeds and 4 resource/window variants. **60/60 matching diagnoses; 60/60 healthy counterexamples correctly forced rediscovery**. These are parameterized synthetic fixtures, not independent production incidents or model benchmarks.
- Matrix: 281 cold planner calls vs 0 learned-replay calls; 281 cold read actions vs 180 learned read actions. Model calls here mean deterministic planner invocations; no LLM token/latency claims.
- `.venv/bin/python run_demo.py --output artifacts/milestone-03` — exit 0; first-run 4 reads/4 planner calls, learned run 3 reads/0 planner calls. Fresh evidence gathered on both runs; UI/failure drift rediscovered the function-timeout fixture. Generated Python Selenium skill imports successfully in tests. Five-resource monitoring sweep includes isolated expired-session outcome.
- `.venv/bin/python -m compileall -q triage tests run_demo.py evaluate.py` — exit 0.

## Tested controls

Read-action allowlist; context/time bounds; stale/future capture rejection; expired-session stop; malformed/model-code proposal denial; repeated-action budget; duplicate evidence detection; page-text and arbitrary-fact exclusion from model input; invalid numeric data cannot imply healthy; no-data classification; irrelevant-query ablation; retained negative evidence; candidate vs held-out-validated workflow; failed revalidation demotion; fresh parameterized reuse; UI/failure drift fallback; no auth-error retry; static code export; concurrent resource failure isolation; consecutive alert dedupe and recovery/recurrence; audit-before-query failure stops execution; audit tamper/restart checks; versioned SQLite registry and corrupted-payload detection; loopback mock HTTP contract; actual Selenium wait/adapter integration with a fake DOM (NOT a real browser); zero-error and fully throttled invocation scenarios; bounded concurrent resource isolation; weekend timezone/interval policy; durable monitor checkpoint/dedupe across restarts, reminder TTL and recovery/recurrence.

## Artifacts

`artifacts/validation/unittest.log`, `evaluation.json`, `selenium-install.log`, `research-search-excerpts.json`.
`artifacts/milestone-03/`: `cold-trace.json`, `warm-trace.json`, `drift-trace.json`, `investigation-explanation.json`, `query-contribution.json`, `skill.json`, `learned_selenium_skill.py`, `monitor.json`, `summary.json`, `audit.jsonl`, `skills.sqlite`.

## Not run / blockers

- Real browser integration: no Chrome/chromedriver discovered. Public Chrome-for-Testing manifest request did not complete before the bounded command timeout. No browser/driver downloaded implicitly.
- OpenCode model-driven coding: configured `opencode/big-pickle` cannot connect to `https://opencode.ai/zen/v1/chat/completions`; prior submissions failed/retried. Blue authored this code. OpenCode shell works; source mirror/integrity evidence is tracked separately in ../OPENCODE.md. OpenCode runtime lacks Python/Node/Bun on PATH; local Python is the test runtime, not OpenCode.
- Live LLM goal-driven exploration: NOT RUN. Structured callback is implemented, deterministic mock planner only exercised.
- Real Dynatrace/CloudWatch selectors, real SSO/NHI, sustained weekend deployment, alert delivery and monitoring changes: NOT RUN and not authorized.
- Production security/full original research acceptance gates: NOT MET. See README limitations; these test results are not proof of deployment readiness.

## Important boundary

The three Selenium contract tests exercise real local HTTP and the installed Selenium wait utilities with a fake DOM driver. They do not execute Chromium, render a page, run JavaScript or establish browser/SSO compatibility. The genuine browser test remains skipped. Weekend scheduling is a tested policy class, not an installed monitoring service.

## OpenCode browser attempt and runtime addition

User requested a test browser in OpenCode. Direct remote inventory found Alpine 3.24.2 / UID11001 with no Python/browser/driver/container tools. Bounded rootless `apk fetch` for Python/Chromium/chromedriver failed on official repository DNS; fetch exit143 at timeout, zero packages downloaded. No system packages/configuration changed, TLS/sandbox safeguards not weakened.

Added `browser_probe.py` (explicit blocked/ready/pass/fail), a non-root container recipe (NOT built/run), and extended the genuine browser test through discovery, held-out workflow validation, generated Selenium script execution and screenshot/JSON artifacts. Local probe executed with `--run`: exit2, status blocked, missing Chrome/chromedriver; this is NOT a browser pass. Three new probe tests pass. Evidence and unblock requirements: runtime/README.md and artifacts/validation/opencode-browser-fetch-attempt.txt.

## ChatGPT existing-project test/review — 21:53 UTC request

Existing ChatGPT OAuth sign-in verified by credential TYPE only. Project-scoped `openai/gpt-6.1-sol` returned CONNECTIVITY_OK and completed a 12-tool-call, read-only review of this existing snapshot. It checked runtime availability but executed NO Python/browser tests in OpenCode because no interpreter/browser/container tool was on PATH. Full report is parent CHATGPT_TEST_REVIEW.md.

Independently reran exact local source:52 discovered=51PASS/1browserSKIP;60/60 cold/reuse and60/60 healthy counterexamples; browser_probe exit2 blocked. Logs under artifacts/validation/chatgpt-request-*.

Local bounded reproductions confirmed TWO review defects: (1) an indefinitely stalled resource prevents sweep return even after a peer completes; (2) exception/blocked reports omit account and region. These are unresolved defects despite the baseline passing suite. Reproduction report: artifacts/validation/chatgpt-findings-reproduced.json. Also identified static acceptance gaps: generated replay calls replay directly rather than automatic drift rediscovery, and Selenium waits do not establish asynchronous query completion. No fixes made in this testing pass.
