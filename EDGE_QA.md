# Edge target validation

- Microsoft Edge/msedgedriver is the primary runtime; explicit Chrome remains supported.
- Python 3.11 regression execution: 58 tests, **57 passed / 1 real-browser skipped**.
- Real Selenium 4 options/services exercised with mocked Edge and Chrome constructors. Both receive explicit executables and isolated profile paths; no Selenium Manager fallback or sandbox bypass.
- Configuration discovery, legacy Chrome environment selection and missing-runtime failures covered.
- Python compilation and Git whitespace validation passed.
- Actual Edge probe: blocked (Edge + msedgedriver absent).
- Actual Chrome probe: blocked (Chrome + chromedriver absent).
- Therefore no real-browser, Windows-host, SSO, or actual LLM navigation success is claimed. Windows launch/cleanup support is code-reviewed, not Windows-executed.
- Version compatibility is delegated to the installed browser/driver pair; use a matching driver. Startup failures surface as failures rather than test passes.
