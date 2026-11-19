# PR first block

## Feature demonstration

**User outcome:** …

**Scenario/source:** synthetic fixture or approved public page; exact PR SHA / clearly labelled app variant; browser/version; viewport.

**Before / after:** embed readable immutable screenshots of the actual component here. For non-UI work include executed observable output.

**Verified:** normal input → observed action/result; assertions; recovery/Undo; session cleanup.

**Not established / blocked:** exact limitations, no inferred success.

Then retain the existing Summary → Architecture → File walkthrough → Tests → Compatibility/limitations sections.

# Major-component review issue

## Visual inventory

| Component/state | Screenshot | Source/scenario | Capture status |
|---|---|---|---|
| … | immutable image | … | captured / blocked |

Use only reviewed synthetic/public images. Include keyboard/focus, empty/loading/error and responsive states when relevant; don't claim an exhaustive audit from a happy-path gallery.

## Separate review requested

Review visual hierarchy, spacing, typography/contrast, clipping/overflow, state clarity, action affordances, consistency and responsive readability. For each concrete finding provide:
- Component + visible evidence.
- Severity/user impact.
- Intended appearance/behavior.
- Smallest specific correction.
- Observable acceptance check.

Label screenshot-only conclusions; accessibility semantics, backend behavior and unpictured states require separate tests. Publish as a separate comment with independent reviewer process/session provenance. Never assert an author-only review is independent.
