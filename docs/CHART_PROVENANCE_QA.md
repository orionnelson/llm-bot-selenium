# Validated observer provenance survives a shortened issue

## Feature demonstration

Outcome: an independent investigation must not accept an older SRE observation as fresh evidence, even if the supplied issue has been shortened since check validation.

Actual executed [demo output](CHART_PROVENANCE_DEMO.json) and [runner](chart_provenance_demo.py):
1. Consented synthetic SRE navigates entity-chart, then uses a semantic dashboard shortcut; two distinct capture IDs are retained in the validated ChartCheck.
2. Supply only the last issue event, without changing the already validated check.
3. Independent alternative-route HTTP chart read returns the first observation ID. Before the fix this gave healthy/failure; after the fix both states become unknown (`reused observer evidence`). Original observer page/history stay unchanged.
4. The SAME check in bounded release monitoring rejects that ID, then accepts fresh evidence: healthy recovery → failure → duplicate suppressed → healthy recovery → loading unknown → healthy recovery → silent healthy → bounded end.

This is actual loopback HTTP, Selenium waits and a fake DOM driver. No rendered browser, model inference, video or production monitoring was run. Source base: `0dbe62b9a973f5fae084cdfc73a4b36116081905`; changed source SHA-256 is recorded in the output.

**Fresh screenshot gate: INCOMPLETE.** This provenance/evaluation API has no UI. Its related synthetic chart fixture was not freshly rendered. Last verified local Chromium missing `libnspr4.so` and remote Grid inability to reach the separate loopback-only fixture are retained blockers, not re-probed or bypassed. Old screenshots are not evidence for this build.

## Tests actually executed

From repository root (project-local Python environment with Selenium installed):

```sh
python -m unittest discover -s tests -v
python evaluate.py
python -m examples.chart_release
PYTHONPATH=.:tests python docs/chart_provenance_demo.py
python -m compileall -q triage tests
git diff --check
cd ui
npm ci --include=dev
npm test
npm run build
```

- Before fix: two new methods reproduced four false-verdict assertion failures, zero errors.
- After fix: 202 Python tests: **197 PASS, 5 opt-in actual-browser SKIP**, zero failures.
- Frontend: **179 PASS**; TypeScript/Vite build PASS (existing large-chunk advisory).
- Existing evaluation: **60/60 diagnosis pairs and 60/60 healthy counterexamples**; connected synthetic UC1/UC2 example PASS.
- New unit and actual HTTP/fake-DOM tests cover shortened issue, replayed healthy/failure, stable independent recovery, same-check release reuse/dedupe/recovery/end and unchanged SRE URL.

## Scope and limits

One source-line replacement, zero net production lines. Reuse the immutable `ChartCheck.observer_evidence` already consumed by ReleaseMonitor; keep checking the supplied issue for compatibility with legacy four-argument checks. No new schema, dependency, framework, scheduler or transport. This does not authenticate adapters, attest consent, detect forged fresh IDs or execute an LLM investigation. Directly constructed checks without full provenance retain legacy supplied-issue protection only. Complete UC1/UC2 browser/model and expanded Studio/full-graph/parallel/replay/handoff acceptance remain open. No deployment, live recording, shared model reload or main release.

Independent native reviewer launch was attempted and blocked by gateway 1008/token mismatch; author scope/DRY review only, not independent acceptance. Original OpenCode author response is complete and live directory status was `{}`; no duplicate author or old snapshot overlay. Owner Studio/services/Grid/canonical files/recordings preserved.
