# Reject ambiguous chart evidence

## Executed feature demonstration — 2026-10-26

A consenting synthetic SRE's validated chart must not turn an expired session into healthy evidence because a JSON object repeats `session_valid` (false, then true). The shared chart reader now rejects duplicate JSON fields, including nested binding/context objects, before recording an observation or evaluating a check.

Fresh affected-surface screenshot **BLOCKED / demonstration visual gate incomplete**: this change is the loopback-only Selenium chart-reader contract, not a Studio UI change. Its synthetic HTML fixture exists, but no new rendered capture was obtained. The sandbox-preserving local Chromium launch failed on missing `libnspr4.so`; the remote Grid is ready but cannot use this adapter to navigate the development process's loopback origin. No origin allowlist or browser security was weakened to get an image. No older screenshot is presented as proof. A future sandbox-capable local browser+driver should render the exact fixture and capture rejection/recovery through the product surface; current contract evidence is not visual acceptance.

Fresh API/CLI evidence: [CHART_JSON_DEMO.json](CHART_JSON_DEMO.json). Actual temporary loopback HTTP server and Selenium waits, with an explicitly **fake DOM driver**, exercised the actual changed reader, observer, investigator and bounded release monitor. No real browser or model inference:

```text
semantic navigation + shortcut -> 2 observed events -> SRE-validated maximum=1
HTTP chart metadata: session_valid=false, session_valid=true
observer capture -> rejected; 0 events appended
independent investigation -> unknown; no trusted evidence
release tick 100 -> unknown, report=true; no evidence/dedupe contamination
unique fresh evidence at 400 -> healthy, report=false
unique value=8 at 700 -> failure, report=true
release end 1000 -> stopped; no additional read
```

Tested source base: `8704ffb0c5b2a6405aeaadc3aac1e5a4bc9faf94`. Changed reader SHA-256: `9b8101ce3ae015e7cb5276e7999eaa176146c7a0912292448cdc0f5b57a55315`. This is an isolated fresh-remote slice, not the owner's deployed/local Studio variant. No deployment or saved workflow changed.

## Reproduce

From repository root using the project environment:

```sh
python -m unittest discover -s tests -p test_chart_browser.py -v
python -m unittest discover -s tests -v
python -m examples.chart_release
python evaluate.py
cd ui && npm ci --include=dev && npm test && npm run build
```

The new HTTP/fake-DOM regression supplies conflicting session-validity, sample-time, chart and nested context/function fields. Before the fix, all four subcases fail because ambiguous evidence is accepted. After the fix, all reject before observer append; investigation and release ticks return unknown without trusted evidence; valid fresh evidence recovers.

Executed: **163 Python PASS, 5 opt-in browser SKIP (168 total)**; **168 frontend PASS**; TypeScript/Vite build PASS; compilation/whitespace PASS; 60/60 diagnosis pairs and 60/60 healthy counterexamples; connected synthetic UC1/UC2 example PASS. Existing bundle-size advisories remain. An initial frontend invocation omitted devDependencies under NODE_ENV=production; corrected with `--include=dev`. Evaluation uses `python evaluate.py`, not a nonexistent `triage.evaluate` module.

## Scope and limits

- Seven net production source lines (five nonblank helper lines) plus one changed parser call; no new dependency, permission, framework, scheduler or schema.
- `object_pairs_hook` rejects duplicate decoded field names at every object depth. Existing payload budgets, visible numeric text, origin/route, freshness, consent and session guards remain.
- Only the consumed chart DOM evidence JSON is tightened; this is not a repository-wide JSON parser migration or validation of every request path.
- Ordinary unique-field charts retain the same behavior. Duplicate fields, even with identical values, are ambiguous and rejected.
- No dishonest-adapter protection, atomic DOM snapshot, root-cause understanding, concurrent executor, live recording, real SRE session, production monitor or full browser/model acceptance claimed.
- Parent scope/DRY review only; independent native reviewer launch remains blocked by gateway-token mismatch. Expanded acceptance/handoff remain open; development schedule stays enabled.
