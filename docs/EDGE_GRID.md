# Microsoft Edge Selenium Grid

## Connected UI

The UI integration now uses the same backend controller for saved tests. See [UI_GRID.md](UI_GRID.md), including real API→Grid startup failure evidence and the distinct static-host deployment gate.

## Scope

`triage.grid.create_driver()` now requests `MicrosoftEdge` using real `EdgeOptions` and `/opt/microsoft/msedge/msedge`. The existing DAG-owned browser-action runner imports this same factory, so its remote sessions use Edge too. No local browser, driver executable, automatic installer or personal profile is needed for this remote path.

Removed the obsolete Chrome-only remote options, native binary path and deployment image. Local Edge/Chrome support remains because existing local tests/probes and callers still use it; deleting that is not necessary for Grid integration. No new dependency, generic arbitrary-site runner or parallel browser framework was added.

## Deploy

The namespace `llms` must exist. From the project root:

```sh
kubectl apply -k deploy/
kubectl -n llms rollout status deployment/selenium-grid
```

The manifest uses `selenium/standalone-edge:4.51.0-20261010`, the existing private fixture sidecar, memory-backed shared memory, non-root execution, no service account token and a private ClusterIP Service. The native browser binary deliberately avoids a wrapper that disables the sandbox. The Kubernetes node/runtime must support sandboxed Edge. Never fix startup by adding `--no-sandbox`, privileged mode or disabling seccomp.

## Checks

Use the project virtualenv with `requirements.lock` installed:

```sh
export SELENIUM_GRID_URL=http://selenium-grid.llms.svc.cluster.local:4444
python -m triage.grid                 # HTTP readiness only
python -m triage.grid --smoke         # actual isolated Edge + synthetic data URL
python -m triage.grid --or9           # explicit read-only public example
```

`--or9` loads exactly `https://or9.ca/`, verifies the final URL, non-empty title and visible body, then quits the isolated session. It does not click, type, log in, take screenshots, export page content or call an LLM. Browser capabilities and sandbox arguments are checked before navigation. A wrong browser, navigation error, unexpected redirect, empty title or hidden body fails the check; no success is inferred from Grid readiness. This is a basic navigation/render smoke check, not a complete functional or HTTP-status assertion for the website.

The default NetworkPolicy deliberately denies browser egress. The loopback synthetic fixture and data URL require no external access. An operator must separately review/permit DNS and HTTPS egress for or9.ca before the public check can pass. Stock Kubernetes NetworkPolicy cannot allow a domain by name; use the cluster's approved FQDN-aware policy or reviewed current destination addresses. Do not delete the policy or allow all egress as a shortcut. Allowing the initial origin does not approve arbitrary redirects, third-party assets or private sites.

Readiness still works while Edge session creation is broken. Inspect:

```sh
kubectl -n llms logs deployment/selenium-grid -c selenium --tail=120
kubectl -n llms describe pod -l app=selenium-grid
```

## Existing browser workflows

The existing consent/revision/URL/action/recording guards remain unchanged. Start the backend as documented in BROWSER_LOOP.md and use its annotated synthetic fixture to exercise Run & Record with Edge. The public or9.ca smoke example does **not** make an unannotated public page eligible for that model/recording adapter. No new public-page recording or arbitrary Selenium commands are exposed through the UI.

The deployment has one browser slot. Existing local two-browser chart tests still require their explicit local runtime; they have not been silently relabelled as remote Grid tests. Simultaneous independent SRE/bot browser acceptance remains a separate capacity and fixture-routing task.

## Regression and explicit live tests

```sh
python -m unittest discover -s tests -v
cd ui && npm test && npm run build
```

Real Grid tests are opt-in and fail (not skip) on an enabled but broken runtime:

```sh
RUN_GRID_EDGE=1 python -m unittest discover -s tests -p test_grid_browser.py -v
RUN_GRID_EDGE=1 RUN_GRID_OR9=1 python -m unittest discover -s tests -p test_grid_browser.py -v
```

## Evidence — 2026-10-24

- Fresh source: blue-master `6ea0459f14e03897f7b81716c23e02eefd93a1de`; isolated working copy, active LAN UI/backend untouched.
- Python: 159 tests, 154 passed, 5 opt-in actual-browser tests skipped. Constructor/regression tests use mocks, not fabricated browser evidence.
- Frontend: 162 passed; TypeScript/Vite build passed. Existing bundle-size advisories remain.
- Real Grid `/status`: ready, one UP MicrosoftEdge 155 slot on Selenium 4.51.0. This confirms advertised capability only.
- Explicit real Grid tests were then enabled: both synthetic and or9.ca checks errored during session creation, before navigation. Grid returned `SessionNotCreatedException` / browser instance exited. Container logs are required to diagnose the underlying startup error; sandbox incompatibility is not assumed proven.
- A separate HTTP fetch from the assistant environment returned 200 for or9.ca; that is NOT Edge/Grid navigation evidence.
- No sandbox bypass, live private recording, cluster policy change, production deployment, active backend replacement or main release performed. Full real-browser/physical UI/model recording acceptance remains open.
