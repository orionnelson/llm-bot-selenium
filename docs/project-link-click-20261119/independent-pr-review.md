**No remaining concrete P1/P2 blocker identified in this exact narrow PR diff.** The four previously reviewed findings remain closed.

### Port review

- **Scope is appropriately narrow:** project-suffix matching, anchor target metadata, guarded new-tab following, observed-change verification, guard-health checks, constructor cleanup, and the explicitly approved `CODER` selector.
- **No owner-only operation variables were imported.** The added code does not reference `operation`, `generatedOperations`, or other newer-owner bookkeeping. Window-tracking variables are initialized before use; `nonlocal followed_window` is valid.
- **The older controller receives the necessary checks:** cancellation/health after reveal, readiness before observing the followed destination, cumulative window checks after observation and capture, and health verification before marking the step verified.
- **Failure paths do not introduce a click retry.** Multiwindow, guard-readiness, guard-loss, and destination-observation failures propagate out of the dispatched-click path.
- **No additional model permissions or public/private boundary relaxation appear.** The model change is the supplied approved selector.

There are intentional additive data-shape changes: observed candidates gain `target`; recorded actions gain `afterUrl` and, when applicable, `navigationContext`. These support the navigation fix. No additional public API or unrelated schema change is visible in the supplied diff.

The explicit `driver_factory=controller.create_driver` in the ported regression harness correctly selects the patched actual-browser controller branch despite the older store’s default factory.

### Acceptance limits

- The reported deployed normal-app run supports the **current deployed variant’s single-instruction path**. It does not establish exact-PR whole-app acceptance or completion of the historical five-step journey.
- Exact-PR focused tests are reported passing; full-suite/evaluator results remain pending. I have not independently executed them.
- Private initial-request blocking and complete worker/egress isolation remain outside the demonstrated evidence.

**Disposition:** No further source correction or additional regression requested from this review. Record the exact-PR full-suite/CI results separately from the deployed-variant screenshots and successful recording.