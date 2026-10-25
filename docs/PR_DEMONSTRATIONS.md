# PR standard — Orion

Before merging, review for duplication, code smells and needless complexity. Orion means **less necessary code**, not more classes/helpers in the name of DRY. Audit what is actually needed at this prototype stage; remove speculative scaffolding and keep existing requested features optional where appropriate. Prefer focused reductions that preserve behavior; do not invent new abstractions or rewrite unrelated features for style alone. Measure net production-code change separately from tests/docs. Add regressions for concrete defects and rerun the existing suite.

Use concise PR documentation in the established format:
0. **Feature demonstration at the very top**: user outcome, actual before/after capture or executed non-UI evidence, scenario/source and verification/limitations. Follow `skills/pr-feature-demo/SKILL.md`; use Selenium Grid for affected UI components.
1. Summary.
2. Mermaid architecture diagram showing actual components and boundaries.
3. File/component walkthrough.
4. Executed test evidence with passed, failed, skipped and blocked clearly separated.
5. Compatibility changes, known limitations and reviewer/run instructions.

Keep README usage product-focused and concise; link detailed architecture and QA docs. Never represent mocked driver construction as real-browser execution, synthetic plans as actual LLM inference, or stubbed Airflow adapters as real workers.

Integration policy reaffirmed by Orion, 2026-10-18 06:12 UTC: automatically merge tested feature PRs into `blue-master` when checks pass and the target/head are verified. Do not wait for another per-PR approval. Keep `main` release merges human-controlled; never bypass checks or branch protection.

Ponytail prompt-only skills are installed under workspace `skills/ponytail*` from reviewed upstream commit09c434ab73ca43761c5d8b0c5d341926c2fba710. Use the smallest complete change; preserve safety/validation. No hooks or telemetry installed.

## Mandatory feature demonstration and separate visual review (owner, 2026-10-25)
Every PR must demonstrate what was implemented before the summary. Read `skills/pr-feature-demo/SKILL.md`. Record actual source/browser/scenario and assertion evidence; inspect screenshots for privacy, publish immutable links, verify the live PR body. Non-UI PRs need meaningful executed evidence, not decorative screenshots. If blocked, put the blocker and honest evidence at the top. For major UI changes capture the major components in a GitHub issue and obtain corrections/acceptance checks from a separate reviewer process/session; identify provenance and never call author self-review independent. Preserve all existing safety, exact-head CI and main-release controls.

## Fresh affected-component evidence — owner correction, 2026-10-25 22:47 UTC
For EVERY functional change, capture a **fresh post-change screenshot of the actual affected/fixed component** and demonstrate its implemented functionality through normal controls (action → observed result, with before/after or recovery where useful). Put this evidence at the TOP of the PR. Links to older screenshots, the prior UI, a generic gallery, test output alone or a text-only feature summary are NOT substitutes. Keep older images only as explicitly labelled comparison context. Record the tested source/build and distinguish rendering evidence from the functional assertion; if fresh capture or execution is blocked, state that blocker and do not mark the demonstration complete. For non-visual changes, show the affected product surface/component plus meaningful executed behavior; if no UI genuinely exists, explicitly explain that and provide actual API/CLI execution evidence rather than inventing a UI. Recapture after subsequent functional changes; do not silently carry screenshots forward from a prior build.
