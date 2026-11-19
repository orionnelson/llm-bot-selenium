# Validate the whole issue before creating a reusable chart check

`ChartCheck.from_issue` previously verified only the last chart. A caller could construct an `IssueBundle` directly with conflicting earlier evidence, an arbitrary action/route, out-of-order capture or untyped session flag, then mint an SRE-validated check from it. This affected the shared UC1/UC2 conversion boundary, not a UI control.

The conversion now reuses `SyntheticObserver.record` over the bounded issue history before evaluating the final chart. SRE validation remains separately explicit; this is structural validation, not consent attestation, proof of browser authenticity or model understanding. Loading/expired earlier context remains permitted by the recorder. Identical repeated facts still work. No new dependency, scheduler, schema or framework.

## Executed evidence

Five pre-fix unit assertions failed. New regression tests cover conflicting facts, arbitrary semantic action, unknown route, unordered timestamps, untyped session state, oversized history and unchanged legitimate conversion. The standalone demo calls actual loopback HTTP with Selenium waits and a fake DOM, attempts forged-issue conversion, then validates a genuine stopped issue, independently investigates via a separate session/alternative route and reuses its check through failure, dedupe, recovery, loading/unknown and bounded end.

See `ISSUE_VALIDATION_DEMO.json` for executed output and source SHA-256. No rendered browser, model inference or production evidence is claimed. No validation UI exists; fresh related chart screenshots remain incomplete (last verified local Chromium missing libnspr4.so; remote Grid cannot reach the separate loopback fixture). No old screenshots substitute for fresh evidence. No shared service, canonical DAG, real recording or monitor was changed.

## Rerun

From repository root with requirements.lock installed:

```sh
python -m unittest discover -s tests -v
python evaluate.py
python -m examples.chart_release
cd ui && npm ci --include=dev --no-audit --no-fund && npm test && npm run build
```

The standalone demo runner is retained in the development workspace; its immutable output is committed here. Existing opt-in browser tests remain separate acceptance gates.
