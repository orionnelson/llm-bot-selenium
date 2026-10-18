# Isolated browser test runtime

## OpenCode attempt — 2026-10-17

User requested a test browser **in OpenCode**. Inspected the existing implementation session and attempted a bounded, project-local package fetch; no system packages/configuration were changed.

Observed remote environment:

- Alpine Linux 3.24.2, non-root UID/GID 11001.
- No Python, Node/Bun, Chromium, chromedriver or Firefox discovered in standard runtime locations.
- No Docker, Podman or kubectl on PATH.
- Official Alpine repositories configured at `https://dl-cdn.alpinelinux.org/alpine/v3.24/{main,community}`.
- Direct `wget` repository check: **bad address `dl-cdn.alpinelinux.org`**.
- `apk fetch --recursive --output /tmp/observability-browser-agent-demo/browser-runtime/packages python3 chromium chromium-chromedriver`, bounded by `timeout 20`: dependency downloads failed with **DNS: transient error**. Terminated at timeout, fetch exit 143. Package directory remained empty. No package installed, no browser executed.

Evidence under `../artifacts/validation/`: `opencode-browser-runtime-probe.txt`, `opencode-browser-fetch-attempt.txt`. The runtime probe is inventory evidence, not a browser test.

## Added test-browser gate

From demo root, when an approved isolated Python/Selenium/browser runtime is staged:

```sh
CHROME_BINARY=/approved/path/chromium CHROMEDRIVER=/approved/path/chromedriver \
  python browser_probe.py --run --output artifacts/browser
```

The runner exits **2 / blocked** when a required runtime is missing, not a fake pass. With dependencies available, it runs the real browser test, rejects skipped tests as success, captures a test log/JSON report, bounds runtime and terminates the test process group on timeout. Only a small environment allowlist enters the synthetic subprocess; ambient cloud credentials/tokens are excluded.

Actual browser acceptance path:

1. Fresh temporary browser profile and home; caller-supplied driver, no implicit downloads.
2. Loopback synthetic UI, goal-driven interface exercised with deterministic mock planner.
3. Capture failure evidence, compile useful-query workflow, validate on a held-out resource.
4. Export/import the generated Python Selenium script and execute it for a third resource with fresh evidence.
5. Verify the finding, reduced read count and zero replay planner calls.
6. Save `synthetic-result.png`, `browser-summary.json`, generated script, test log and runtime report.

This remains a deterministic browser test, **not live LLM investigation or SSO validation**.

## Container recipe (NOT built or run here)

`runtime/Dockerfile` supplies matched distro Chromium/chromedriver plus Python/Selenium in a dedicated non-root test image. Build context is demo root:

```sh
docker build -f runtime/Dockerfile -t observability-selenium-test .
docker run --rm --network=none observability-selenium-test
```

For retained artifacts, mount a writable directory owned by UID 11001 at `/app/artifacts`. This recipe has not been built: neither OpenCode nor OpenClaw currently provides a container build/run tool. Base image and distro package versions must be digest/version-pinned for reproducible deployment; Python dependencies are version-locked already.

Run in an isolated approved sandbox with no cloud credentials, no existing browser profile/SSO state and no production network access. Loopback remains available with `--network=none`. The default Chrome sandbox stays enabled; **do not add `--no-sandbox`, run privileged, disable TLS checks or change shared runtime security settings** to make a test pass. If sandbox support is unavailable, report it and use an approved browser runtime instead. Image startup/browser compatibility is unverified until actual execution succeeds.

## Exact unblock

Provide either an approved prebuilt browser/Python test image/runtime attached to the OpenCode project, or approved DNS/HTTPS access to the configured package repositories plus a supported installation/runtime path. Rootless fetching alone does not install the required shared-library tree. Do not repeatedly retry unchanged DNS failures or silently modify the shared OpenCode image/configuration.
