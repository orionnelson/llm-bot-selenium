# Investigation → learned Selenium workflow: synthetic prototype

**Research harness, not production-ready automation.** No internal Dynatrace/AWS access, credentials, real SSO, deployment or cloud changes. The initial Zen model could not reach its upstream; Blue authored this implementation. OpenCode now successfully uses ChatGPT OAuth with `openai/gpt-6.1-sol` for project inspection/review. That model access is distinct from evaluating the browser agent itself. See `test-results.md` for validation boundaries.

## What exists

- `triage/core.py`: independent action/context/freshness/session policy, structured planner callback, deterministic test planner, evidence verifier, diagnostic trace, query-contribution ablation, candidate/validated skill lifecycle, replay and drift fallback, static Selenium script exporter.
- `triage/fixtures.py`: synthetic dependency-timeout, function-timeout, throttling, healthy, missing-data and unknown scenarios, including malicious page text.
- `triage/selenium_port.py`: Selenium WebDriver adapter for **our local mock contract**, not a Dynatrace page adapter. Explicit waits; read-only controls; loopback-only origin; caller-provided isolated driver. No automatic browser or driver downloads.
- `triage/mock_server.py`: local mock UI with query controls and typed evidence. No external assets or real product connection.
- `triage/monitor.py`: bounded concurrent **single sweep** with separate ports per resource, failure isolation, deduplication and proposed monitoring measures. `triage/weekend.py` adds timezone/interval policy and optional SQLite checkpoint/dedupe with TTL and recovery/recurrence tests. No live weekend scheduler or alert delivery.
- `triage/audit.py` and `triage/registry.py`: single-writer hash-chained query audit and versioned SQLite skill registry. Checksums detect corruption, not an attacker able to rewrite the whole store.
- `evaluate.py`: 60 seeded synthetic cold/reuse pairs and healthy counterexamples.
- `run_demo.py`: exports cold/warm/drift traces, query-contribution records, validated skill, generated Selenium Python module and monitoring report.

## Run without dependencies

Python 3.11+ standard library is enough for deterministic and HTTP tests:

```sh
cd llm-bot-selenium
python3 -m unittest discover -s tests -v
python3 run_demo.py --output artifacts/demo
python3 -m triage.mock_server
```

## Browser target: Microsoft Edge

Use **Edge + matching `msedgedriver`** (Selenium 4). Install `requirements.lock` in a virtualenv and supply executable paths; the project never downloads browsers/drivers automatically.

```sh
python browser_probe.py --browser edge --edge /path/to/msedge --driver /path/to/msedgedriver --run
```

Windows PowerShell:

```powershell
python browser_probe.py --browser edge --edge "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --driver "C:\tools\msedgedriver.exe" --run
```

Alternatively set `SELENIUM_BROWSER=edge`, `MSEDGE_BINARY`, and `MSEDGEDRIVER` before running the browser test. Edge is the default; direct test execution requires explicit environment paths.

**Chrome remains supported:**

```sh
python browser_probe.py --browser chrome --chrome /path/to/chrome --driver /path/to/chromedriver --run
```

The original `CHROME_BINARY` + `CHROMEDRIVER` setup still selects Chrome unless `SELENIUM_BROWSER` overrides it.

The probe writes runtime status, logs, and—on genuine browser success—a screenshot and browser/version summary under `artifacts/browser`. Ready executable checks and mocked constructor tests are **not** real-browser passes. No Edge/Chrome binaries are available in the current environment; the real-browser test is skipped.

Runs use temporary profiles, keep sandboxing enabled, and target only the synthetic loopback UI. The [runtime image recipe](runtime/README.md) remains **Chromium-only** and unbuilt, not an Edge installation recipe.

## Learning demonstration

Cold deterministic investigation visits a distracting tags query followed by invocation health, failure events and a throttling rule-out. Greedy ablation removes the irrelevant tags step but preserves diagnostic evidence and useful negative evidence. A held-out synthetic incident validates a parameterized skill; a new function/time range reuses it with zero planner calls. Fresh evidence is collected for every replay. UI-contract or diagnosis drift triggers bounded rediscovery; authentication/context/freshness failures stop rather than trigger more attempts.

Generated module: `artifacts/demo/learned_selenium_skill.py`. It calls the shared Selenium adapter and verifier. It contains static serialized workflow data, not model-generated executable code or saved credentials. It can only drive the local mock UI until a separately approved production adapter exists.

## What this does NOT prove

- `MockPlanner` is a fixed deterministic baseline, **not an LLM**, zero-shot Dynatrace exploration, or generalized goal understanding. `StructuredPlanner` is a model callback interface; no real model was evaluated.
- The verifier and query-value ablation use **synthetic evidence rules**. They do not establish real causal attribution or root-cause correctness. One held-out fixture is smoke coverage, not sufficient production promotion evidence.
- Adapters currently recognize an operator-owned mock query catalog. A real observer must discover semantic controls on unfamiliar layouts, handle navigation/query input safely, and test pagination/loading/permission states. Built-in tool knowledge remains necessary even if the user need not know Dynatrace.
- The mock server's result JSON exists in the page source before the read button is clicked; it tests the adapter contract, not a faithful asynchronous data-loading implementation.
- Top-level origin checks do not stop redirects/subresources before a request leaves the browser. Real deployment needs independently enforced egress controls and read-limited identity. No network-isolation certification is claimed.
- Fresh capture timestamps do not alone establish underlying telemetry freshness. Real adapter must verify metric sample timestamps, query completion, exact windows and completeness.
- Trace facts are synthetic. The demo omits raw page text and minimizes model fields, but has **no complete production redaction pipeline**; do not ingest real logs.
- Monitoring defaults to in-memory dedupe; optional SQLite state implements durable dedupe/TTL. Cross-process task ownership, actual alert escalation/delivery and recovery notifications are not implemented. Blocking adapters need enforced per-task deadlines/process isolation; ThreadPool alone cannot cancel a stuck browser.
- No automated alarm creation/remediation or production skill promotion.

## Next work

1. Inspect and execute this Selenium adapter in an approved browser runtime; expand timing/layout/adversarial tests.
2. Add a model on synthetic-only observations, compare against deterministic baseline, and implement general semantic discovery rather than fixed catalog ordering.
3. Validate useful-query selection with held-out alternate causes and missing/contradictory evidence, not just successful traces.
4. Harden the implemented local registry and query audit: add TTL/rollback/revocation, cross-process ownership, audit navigation/denials as well as reads, query-cost/time budgets and stronger schema/context verification.
5. Connect the tested weekend policy and durable per-function dedupe to a real scheduler only after authorization; add task ownership/deadlines, trigger-specific monitoring and alert delivery policy.
6. Pilot real SSO/NHI only with an approved identity lifecycle and explicit read permissions; stop on MFA/session expiry.
