---
name: pr-feature-demo
description: Demonstrate implemented behavior at the top of every PR, choose an observable safe feature scenario, collect real execution evidence and Selenium Grid UI screenshots, and route major-component visual captures to an independent UI-review issue. Use when preparing, updating, reviewing or publishing any pull request or feature demo.
---

# Demonstrate the feature first

For every PR, put **Feature demonstration** before the summary, architecture and walkthrough. Read the repository's existing PR standard; add this gate without replacing tests, CI, privacy or release controls. Use `references/demo-template.md` for the evidence block and visual-review issue.

## Decide what to demonstrate

1. State the user's intended outcome, not the changed function name.
2. Identify the smallest observable success condition. Example: selecting one wire enables Disconnect; clicking removes only that wire; Undo restores it.
3. Choose a safe representative fixture and real input path. Exercise the actual affected component through its normal controls. Do not alter DOM/CSS to disguise defects or force an otherwise blocked action.
4. Choose before/after states and one relevant error, cancellation or recovery state. Capture major changed components at a readable viewport; avoid redundant screenshots.
5. Execute, assert and record outcomes. A generated plan, model response or screenshot alone does not prove an action succeeded.

## Capture evidence

- Use the project's Selenium Grid for browser/UI evidence when available. Prefer the exact PR build; otherwise label deployed/local variant, source hash and differences explicitly.
- Record browser/version, source commit or deployed bundle hash, viewport, scenario, actual steps, assertions and limitations. Always close owned sessions; preserve existing processes, saved workflows and unrelated sessions.
- Use synthetic/public owner-approved data. Never publish passwords, authorization headers, private recordings, personal data or hidden form values. Inspect images before upload. Do not send private screenshots to an external reviewer/model.
- Capture the real component region and its states. Keep an unaltered original; label any crop or annotation. Link immutable committed image URLs and check the remote blob hashes and live PR body after publication.
- For non-UI changes, show meaningful executed API/CLI/test output instead of irrelevant UI screenshots. If execution is blocked, lead with the exact blocker and the highest-fidelity evidence actually collected; never invent a successful demo.
- State what evidence does **not** establish (e.g. synthetic vs production, app variant vs exact PR build, mocked model vs actual inference).

## Integrate and review

- Preserve the normal summary, actual architecture, file walkthrough, executed tests and limitations below the demonstration. Recheck evidence whenever code changes; docs-only updates must not inherit old exact-head CI.
- For major UI work, create/update a GitHub issue containing an inventory of major components, readable screenshots, source/scenario metadata and missing/blocked states.
- Hand the screenshots to a **separate reviewer process/session**, not the implementation author's self-review. Ask for evidence-based severity, intended appearance, specific corrections and acceptance checks. Post the review as a distinct issue comment and identify its provenance. Say when independence is blocked; do not relabel self-review.
- Treat review notes as proposed fixes, not authorization for unrelated redesign. Keep issue/PR links and publication receipts in the project's durable status.
- Follow existing exact-head CI/merge policy. Never bypass checks or release to a human-controlled main branch just to complete a demonstration.

## Fresh affected-component evidence — owner correction, 2026-10-25 22:47 UTC
For EVERY functional change, capture a **fresh post-change screenshot of the actual affected/fixed component** and demonstrate its implemented functionality through normal controls (action → observed result, with before/after or recovery where useful). Put this evidence at the TOP of the PR. Links to older screenshots, the prior UI, a generic gallery, test output alone or a text-only feature summary are NOT substitutes. Keep older images only as explicitly labelled comparison context. Record the tested source/build and distinguish rendering evidence from the functional assertion; if fresh capture or execution is blocked, state that blocker and do not mark the demonstration complete. For non-visual changes, show the affected product surface/component plus meaningful executed behavior; if no UI genuinely exists, explicitly explain that and provide actual API/CLI execution evidence rather than inventing a UI. Recapture after subsequent functional changes; do not silently carry screenshots forward from a prior build.
