# Edge target validation

- Microsoft Edge/msedgedriver is the primary runtime; explicit Chrome remains supported.
- Python 3.11 regression execution: 62 tests, **61 passed / 1 real-browser skipped**.
- Real Selenium 4 options/services exercised with mocked Edge and Chrome constructors. Both receive explicit executables and isolated profile paths; no Selenium Manager fallback or sandbox bypass.
- Configuration discovery, legacy Chrome environment selection and missing-runtime failures covered.
- Python compilation and Git whitespace validation passed.
- Actual Edge probe: blocked (Edge + msedgedriver absent).
- Actual Chrome probe: blocked (Chrome + chromedriver absent).
- Therefore no real-browser, Windows-host, SSO, or actual LLM navigation success is claimed. Windows launch/cleanup support is code-reviewed, not Windows-executed.
- Version compatibility is delegated to the installed browser/driver pair; use a matching driver. Startup failures surface as failures rather than test passes.

## Pre-merge DRY review

- Centralized browser environment names, executable candidates and Selenium class names in one small immutable BrowserSpec map; probe, constructor and real-browser test share it.
- Shared executable validation and child-environment mapping; removed unused import and duplicated log writes.
- Fixed two concrete edge cases: explicit Edge binary could lose to ambient Chrome selection; relative executable paths broke when child CWD changed. Added four regressions.
- Centralized conflicting-option validation; invalid CLI arguments no longer create output directories.
- Full rerun: 62 tests, 61 passed, one real-browser skipped. Compilation and whitespace checks passed. No unrelated monitoring refactor or real-browser claim.
