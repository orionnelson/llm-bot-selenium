The screenshots support the successful read-only replay flow. The two older findings are addressed in the main replay UI: progress is selection-scoped, and outcomes use the selected step. Current source still exposes keyboard/modal accessibility defects and an asynchronous recording-selection race; these need targeted browser reproduction, separate from the passed controls run.

## Independent read-only review — current deployed version

**The supplied evidence supports the successful replay controls run, but does not establish coverage of all app flows or acceptance of exact PR61.** I found **three actionable P2 issues in current source** requiring targeted browser reproduction. No P1 defect is established by these screenshots.

### Provenance and scope

- Independently inspected all **seven requested screenshots** and `receipt.json` under:
  `/srv/opencode/data/opencode/tool-output/sre-grid-studio/state/current-version-review-20261119/`
- Reviewed current `ui/src/JourneyRecorder.tsx`, `GridSessionView.tsx`, `App.tsx`, `styles.css`, and directly related recording/replay components.
- Deployment identity supplied by the parent:
  - Bundle: `index-Bo2ZZklr.js`
  - SHA-256: `8caef34b746848c6cb4b854e456ef46edee76e7afad1f3e007898939ce2afcff`
- **This is the current owner-deployed variant, not the older exact PR61 build.** Source findings below are not independent proof that this bundle contains identical source.
- I performed **no execution, network requests, edits, or new browser interactions**. Behavioral passes below are attributed to the parent’s run/receipt, not my own testing.

## Actionable findings

### 1. P2 — Global Space shortcut suppresses native keyboard activation of buttons

**Evidence: source-confirmed; browser reproduction pending.**

**Reference:** `ui/src/App.tsx:154`; affected replay controls at `JourneyRecorder.tsx:77–82`.

The window-level `keydown` handler excludes inputs, textareas, selects, and editable content. For Space outside `.workflow-canvas`, it then calls `preventDefault()` and toggles demo playback. It does not exclude buttons, links, summaries, or tab controls.

Consequently, focused replay buttons outside the canvas have their normal Space activation intercepted. This also applies to the explicit Space branch while viewing a recording preview.

**Reproduction**
1. Open a saved recording.
2. Use Tab to focus **Code**, **Before**, **Next step**, or **Play step replay**.
3. Press Space.
4. Check whether the focused control activates and whether hidden demo playback changes instead.

**User impact:** Keyboard users cannot reliably operate primary replay controls using standard button activation. An unrelated demo playback state can change while the user is reviewing recording evidence.

**Minimal correction:** Scope demo shortcuts to the intended demo surface; respect `event.defaultPrevented` and exclude interactive elements. Preserve native Space behavior on controls.

**Acceptance check:** Space activates each focused replay button/tab exactly once; no demo clock/playback state changes. Arrow/Home/End tab navigation continues working without triggering unrelated global shortcuts.

---

### 2. P2 — Full DAG modal declares itself modal without implementing modal keyboard behavior

**Evidence: source-confirmed; keyboard behavior not tested in the supplied run.**

**References:**
- `ui/src/RecordingDAG.tsx:14,51,58`
- `ui/src/App.tsx:154`

The Full DAG overlay has `role="dialog"` and `aria-modal="true"`, but the component has no focus transfer, focus containment, Escape handling, or trigger-focus restoration. The App Escape handler clears App’s separate `modal` state; it does not clear RecordingDAG’s local `full` state.

**Reproduction**
1. Keyboard-focus **Full DAG** and press Enter.
2. Observe focus immediately after opening.
3. Tab/Shift+Tab through the dialog boundary.
4. Press Escape.
5. Close the dialog and inspect the restored focus location.

**User impact:** Keyboard and assistive-technology users can remain on background controls despite the modal announcement, navigate into obscured content, and cannot dismiss this dialog with Escape. Background Record controls remain relevant to this failure.

**Minimal correction:** Use a shared accessible modal or native modal dialog implementing initial focus, contained focus, Escape dismissal, and restoration to **Full DAG**.

**Acceptance check:** Opening moves focus inside; Tab cycles within the dialog; Escape closes it; closing restores focus to the trigger; background controls cannot receive focus or activation while open.

---

### 3. P2 — Overlapping recording loads can replace the latest user selection with an older request

**Evidence: source-confirmed race condition; deployed reproduction pending.**

**References:** `ui/src/JourneyRecorder.tsx:63,72`.

`open(id)` awaits `browserRun(id)` and unconditionally calls `setRun(value)`. The recording selector remains enabled during those requests. There is no request-generation check, cancellation, or selected-ID guard.

**Reproduction**
1. With saved recordings available, delay response A using controlled browser request interception.
2. Select recording A, then recording B.
3. Allow B to resolve first, then A.
4. Observe the selected recording, DAG, frame, source, and outcomes.

**User impact:** A slower earlier request can silently take the reviewer back to the wrong recording. Even if the resulting panels remain internally synchronized, the evidence being inspected no longer corresponds to the user’s latest selection.

**Minimal correction:** Track a monotonically increasing load token and apply success/error results only for the latest request; alternatively cancel superseded loads.

**Acceptance check:** With A/B responses deliberately reversed, B remains selected and all panels show B. A superseded failed request must not add an error to B’s successful view.

## Screenshot-confirmed observations

### Mobile overview is fitted, but its node content is not readable at normal scale

**References:** `automatic-recording-mobile-full.png`, `expanded-mobile-graph.png`; `styles.css:108–109,118,130–131`; `RecordingDAG.tsx:18,51–53`.

The collapsed mobile screenshot shows five nodes fitted into the available width, with labels/status text reduced to only a few rendered pixels. The expanded screenshot shows substantially readable labels and vertical layout.

**Disposition:** This is a confirmed limitation of the overview, **not evidence that mobile graph inspection is blocked**: Expand graph exists and the receipt reports its readable-scale check passed. Avoid describing the fitted overview itself as readable. If readability in collapsed mode is required, keep only a legible short label/status there and expose details through the expanded view.

The mobile code screenshot has readable surrounding controls and intentionally horizontally overflowing code. Desktop code visibly has an internal horizontal scrollbar. **These images do not establish a page-wide horizontal overflow defect.**

Desktop auxiliary labels and the recording selector remain small; `styles.css:19` explicitly assigns the session selector `9px` text. This warrants zoom/target-size checks, but I would not elevate it above the functional findings without measured interaction failures.

## Verification of the two older findings

| Earlier finding | Actual current source | Assessment |
|---|---|---|
| Cross-recording execution progress in the replay viewer | `JourneyRecorder.tsx:37–39,83` associates progress with a selection ID and suppresses mismatched progress. `ReviewedReplay.tsx:21–25` forwards only progress owned by the component; line 106 of JourneyRecorder keys it by recording. | **Addressed in the main viewer’s source.** Do not repeat the old finding unchanged. |
| Unscoped aggregate outcomes | `JourneyRecorder.tsx:64–68,93–101` derives task evidence, results, facts, articles, and screenshot links from the selected step. `RecordingDAG.tsx:31–32,55` also uses selected task/step evidence. | **Addressed in current source.** The outcomes screenshot visibly presents “Step outcome” and the selected instruction/result. |

**Residual distinction:** `ReviewedReplay.tsx:28,47` still restores a global active/latest execution and renders it inside the Advanced section, even when ownership filtering prevents forwarding it to the recording viewer. That section labels it “Live backend execution” and distinguishes its frames, and execution is OFF. This is **not proof of the original main-viewer bug recurring**. If investigated, capture the expanded Advanced section and verify whether the restored run’s association is sufficiently clear.

## Coverage matrix

Screenshot names below are relative to the evidence directory above.

| Flow / state | Evidence inspected | Coverage |
|---|---|---|
| Desktop recording DAG, selected node | `automatic-dag-before-desktop-full.png`, `automatic-dag-after-desktop-full.png` | Visually confirmed five-node graph and selected step |
| Before / After evidence | Same two images | Distinct captions and timestamps visible; exact association passed per receipt |
| Desktop selected task source | `recording-code-desktop-full.png` | Source, provenance disclosure, export control visible |
| Desktop selected-step outcomes | `recording-outcomes-desktop-full.png` | Instruction/result/status visible; full result collapsed |
| Mobile automatic graph fit | `automatic-recording-mobile-full.png` | Fitted overview visible; text tiny |
| Mobile expanded graph | `expanded-mobile-graph.png` | Readable vertical layout visible; image covers only part of graph |
| Mobile source | `recording-code-mobile.png` | Controls/source visible; cropped component image |
| Nine-node recording and node/step/frame/source synchronization | `receipt.json:13,21` and parent report | Behavioral pass reported; not independently demonstrated by the seven images |
| Full DAG modal and generated source | `receipt.json:20` | Functional pass reported; modal keyboard accessibility untested |
| Downloaded Python AST validity | `receipt.json:12` | Pass reported; download not independently retrieved here |
| Draft preservation, editor restoration, preview Ctrl+S | `receipt.json:11,22–24,52` | Pass reported; screenshots alone cannot prove preservation/no writes |
| Original frame opening | `receipt.json:16–17` | Pass reported |

### NOT TESTED / additional captures needed

- Keyboard-only replay, modal focus behavior, screen-reader output, and browser zoom/reflow.
- Recording selection with overlapping, failed, or delayed requests.
- New recording creation, live updates, follow-live/manual selection, Stop/cancellation, interrupted/failed recordings, and empty history.
- Missing, expired, or failed screenshot delivery. `GridSessionView.tsx:25–27` checks whether an image path exists, but has no image-load error fallback; **misleading display after delivery failure remains a reproduction hypothesis**, not a screenshot-confirmed defect.
- Copy-to-draft replacement, explicit Save/conflicts, authoring/editing, import/export JSON, templates, demo history, Schedule, and Share.
- Advanced executor operation, which remains disabled.

**Recommended issue provenance:** Attach the three source-backed P2 findings separately from the successful current-deployment replay receipt. Request targeted reproductions/captures for those findings and the uncovered flows; do not characterize this review as “all flows covered,” exact PR61 acceptance, or authorization to enable execution or merge.