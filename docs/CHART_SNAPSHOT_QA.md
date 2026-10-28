# Stable chart metadata during evidence collection

The consenting SRE observer, separate investigation and reusable release check all use
`SeleniumChartPort.read_visible`. It now reads the chart evidence attribute again
after collecting numeric text. A changed or removed attribute rejects the whole
read rather than combining new visible text with old session/scope/evidence metadata.
Visibility and URL checks remain in place. Two production lines, no new dependency.

## Executed scenario (2026-10-28 14:00 UTC)

Fresh baseline: `d07d5c2d8f3cce7e7ba2e26fdecdc3610add5f17`.
`CHART_SNAPSHOT_DEMO.json` is output from a separately executed loopback HTTP scenario
using actual Selenium waits with the fake DOM driver (NOT a rendered browser):

1. Synthetic person navigates and submits a semantic chart shortcut, producing an issue.
2. Explicit SRE validation creates one reusable ChartCheck.
3. Simulated metadata changes during the read (session becomes invalid): observer records
   zero events, alternative-route independent investigation returns unknown/no trusted evidence,
   bounded release tick reports unknown without polluting evidence dedupe.
4. Fresh stable chart recovers healthy at 400; failure at 700 reports; repeated failure at
   1000 deduplicates; release ends at 1300. No sleeping scheduler or alert send.

Two new regression methods also cover loading, replaced evidence ID and removed payload.
Before the guard: eight failing assertions, including false-healthy investigation.
After: 192 Python tests run, **187 PASS / 5 opt-in browser SKIP**; 179 frontend PASS;
TypeScript/Vite build PASS (existing chunk-size warnings). 60/60 diagnoses and 60/60
healthy counterexamples; connected synthetic UC1/UC2 example, compileall and diff checks PASS.

From repository root, with project-local Selenium environment:

```sh
python -m unittest discover -s tests -p test_chart_browser.py -v
python -m unittest discover -s tests -v
python evaluate.py
python -m examples.chart_release
cd ui && npm ci --include=dev --no-audit --no-fund && npm test && npm run build
```

## Limits / acceptance gates

One extra bounded WebDriver attribute read per chart read. Conservative raw-string
comparison rejects even equivalent reserialization; callers retry only on their next
explicit read/tick, never automatically repeat actions. This is NOT an atomic DOM
snapshot: value-only changes, changes after the final check, and away-and-back mutations
between checks are not detected. It does not prove real model understanding, browser
rendering, or production readiness. Discarded metadata is not trusted as session expiry;
the release reports unknown and may retry its next scheduled slot.

**Fresh affected-component screenshot gate INCOMPLETE/BLOCKED.** This is the shared
nonvisual chart adapter; ReleaseMonitor has no UI. Related synthetic chart HTML was not
rendered in this run. Last verified local Chromium lacks libnspr4.so; the ready remote
Grid cannot reach the development-loopback-only fixture. Unchanged blockers are carried,
not repeatedly probed or bypassed. No older images used as fresh proof. New actual
browser/model/video acceptance NOT RUN. Owner deployed Studio/instruction-retry repair,
canonical workflows, Grid and recordings were not changed. Full UC1/UC2/expanded Studio
execution and handoff gates remain open; development stays enabled.
