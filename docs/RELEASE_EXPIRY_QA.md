# Stop a release on typed session expiry, even with unusable evidence

## Feature demonstration — fresh API execution

The SRE's explicitly consented synthetic navigation and shortcut produce an issue and an SRE-validated `ChartCheck`. The bot independently uses the alternative entity route. The SAME check feeds caller-driven, bounded 300-second release ticks.

Run from repository root:

```sh
PYTHONPATH=.:tests python docs/release_expiry_demo.py
```

Fresh output: [RELEASE_EXPIRY_DEMO.json](RELEASE_EXPIRY_DEMO.json). It includes the tested `triage/chart_checks.py` SHA-256 and fresh remote base. The adapter uses actual loopback HTTP and Selenium waits, but a **fake DOM**, not a rendered browser or actual model.

- Stable adapter identity + literal `session_valid=False` + malformed URL-shaped evidence reference now reports unknown/no reference and stops the release. A later tick cannot restart it or perform another read. Evidence/replay state is not contaminated.
- Falsey but untyped session values (`0`, empty string, `None`) remain unknown, not an authenticated expiry signal. They no longer incorrectly stop the plan; the next valid due read recovers. String `"false"` is also unknown, never healthy.
- Expiry from a switched browser identity cannot stop the original plan. Explicit caller Stop during an in-flight return/error still suppresses the result.
- A stopped plan is not silently restarted after a valid session returns. The HTTP regression explicitly constructs a new plan using the SAME SRE check.
- Fresh independent alternative-route failure and the usual same-check 300-second failure/dedupe/recovery/loading unknown/recovery/end sequence still pass.

The change affects a Python monitoring API, not a UI component. **Fresh related-component screenshot gate remains INCOMPLETE**: the related chart fixture was not freshly rendered. Historical local missing `libnspr4.so` / remote Grid-to-development-loopback limitations are carried, not re-probed, bypassed or replaced with old images. This output does not establish actual browser, model, video, production monitoring or whole-product acceptance.

## Smallest implementation

Keep typed expiry separately from caller Stop while validating evidence. Recognize it only after the adapter identity check; apply it after the existing exception-to-unknown path. Otherwise an early `stop()` would cause the explicit-Stop suppression branch to discard the required unknown result. This also avoids truthiness-based termination for malformed session state. Net production change: **+2 lines**, no new dependency, schema, scheduler, transport or permissions.

## Executed regression

Before fix: three new methods reproduced **9 failed assertions, zero errors**. After fix: **228 Python PASS /5 opt-in actual-browser SKIP (233 total)**; frontend **179 PASS**, TypeScript/Vite build PASS. Deterministic evaluation:60/60 diagnoses and60/60 healthy; connected UC1/UC2 example PASS. Compilation/whitespace PASS. Actual execution logs are retained by the development report.

This remains a single-owner, in-memory bounded monitor. A boolean expiry flag is a validated adapter assertion, not identity authentication, reauthentication or evidence authenticity. Rejected untyped states still use the existing unknown-report cadence/dedupe policy. No live schedule/alerts, service changes, real-person recording, model reload or deployment.
