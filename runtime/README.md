# Browser runtime

Install `requirements.lock` in a virtualenv. Provide an existing browser and matching driver; no automatic downloads or system changes.

**Edge (primary):**

```sh
python browser_probe.py --browser edge --edge /path/to/msedge --driver /path/to/msedgedriver --run
```

**Chrome (optional):** use `--browser chrome --chrome /path/to/chrome --driver /path/to/chromedriver`.

The runner uses a temporary profile/home, excludes ambient credentials, limits execution time and stops driver descendants on timeout. Sandboxing stays enabled. It only opens the synthetic loopback UI.

Exit `2` means missing runtime, not success. A real pass produces a screenshot, browser/version summary and test log in `artifacts/browser`; a skipped test cannot pass the gate.

Both browsers are unavailable here. Windows commands are in the root README. Container packaging is deferred until there is a tested runtime; the unbuilt Chromium-only recipe has been removed. No SSO, production access or actual LLM-led investigation is validated.
