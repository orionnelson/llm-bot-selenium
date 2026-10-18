# Edge/Chrome validation

**Executed:** Python 3.11, 61 tests: **60 passed / 1 real-browser skipped**. Compilation and whitespace checks passed. Full output: `test-results-latest.txt`.

Both constructors use real Selenium options/services with mocked launches. Regressions cover browser selection, explicit executable paths, relative-path resolution and conflicting options.

**Blocked:** actual Edge/Chrome execution; neither browser/driver pair is installed. Windows launch/cleanup code has not run on Windows. No SSO, production monitoring or actual LLM investigation pass is claimed.

## Scope review

- Keep: Edge + Chrome, explicit drivers, isolated profiles, timeout cleanup, synthetic UI, evidence/learning tests and CI.
- Simplify: replace BrowserSpec class/registry with two environment-name pairs; remove wrapper helpers and duplicate output handling.
- Defer: container packaging; remove the unbuilt Chromium-only Dockerfile. No automatic installers, deployment or new orchestration.
- Retain existing optional audit/registry/weekend modules because they implement the requested learning/monitoring prototype; they are not production acceptance or prerequisites for the browser test.

Runtime/probe source: **178 → 139 lines** versus the first PR #4 revision; **153 → 139** versus merged PR #3. This is a source-line comparison, not minification or a performance claim. The removed container recipe is a further 18 lines.
