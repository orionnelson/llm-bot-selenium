# Concrete UI review corrections

Scope: findings from issues #33/#34, rechecked against the newer instruction/session UI. The older gallery is comparison context only, not evidence of these fixes. Fresh affected-component Grid captures and functional assertions are required before acceptance.

| Finding | Concrete correction | Acceptance |
|---|---|---|
| P1 unreadable graph titles | Zoom-aware title sizing; below 75% use a semantic overview that omits descriptions but retains titles, control predicates and route legends. Desktop titles wrap at word boundaries without ellipsis; tiny topology views use explicit abbreviations with full accessible names and inspector details. | At the desktop template fit, measure rendered title size at least 13.5px (baseline 5.79px); screenshot the actual graph. Extreme overview scales still truncate long labels, rather than pretending all details fit. |
| P1 faint/overlapping connections | Non-scaling 2px paths, cyan selected edge, and a dedicated dashed repeat path below all cards with an explicit REPEAT label. | Native pointer wire selection/disconnect/Undo passes; repeat path bounds extend below all card bounds; fresh loop screenshot shows route. |
| P2 shallow code inspector | Python/Task DAG/Steps/LLM tabs request a 420px inspector; explicit Expand/Restore control; full-width code mode, 12px code and a 220px Python editor. Reset tab scroll to its start. | Measure inspector/editor; toggle sizing; show the actual edited component. Bound height through existing workspace limits. |
| P2 saved-versus-draft ambiguity | A reachable Compare saved browser policy dialog separates the current editable draft from a read-only saved canonical snapshot and node identity. Correct the draft editor legend. | Open it through Node Config; show distinct draft/saved target and mode; do not Save or mutate canonical state. |
| P2 generic contrast/density recommendation | Use #B7C6D9 secondary and #9AAEC3 muted text, 11px helper labels and 12px palette labels; disabled controls remain distinct. | Fresh native-size component images; these specific colors/sizes do not claim a whole-app accessibility certification. |
| P2 vague “two active tabs” report | Baseline DOM actually had one active library tab, so do not invent a state bug. Strengthen the visual selected style, add real tab semantics/roving focus and Left/Right/Home/End activation. Make icon tooltips visible to mouse and keyboard; strengthen palette drag affordances. | Assert one selected tab per group and keyboard activation; screenshot selected state and a tooltip. |
| P2 no-session triage transport | The old transport stack is no longer part of the session-only layout; do not resurrect it. Restore the broken Snippets entry point as a triage modal, with explicit empty state and no pretend transport. | Open the empty modal; load a labelled fixture, clip/save a snippet, inspect the saved library item; no browser action. |
| P3 DAG reimport guidance | Replace anonymous flex text columns with a stacked command/note block. Restore reachable Import/Export buttons with existing size/format validation and inert source semantics. | Screenshot the note, import a synthetic local JSON file through the real file input, confirm the draft changes without a backend commit. |
| P3 generic inspector/debugger empty states | Use tab-specific selection guidance. Legacy debugger is absent from current layout; add consistent spacing in the retained component stylesheet without claiming an obsolete panel was retested. | Deselect graph, select Task DAG, show “Select a node to inspect its task definition.” |
| Missing hidden history coverage | The old mixed right-pane stack was replaced; recorded sessions remain in the visible session picker. Restore separate local Demo history/export/replay in a modal. | Show empty history, create/pause a labelled deterministic demo, show its row and replay it without browser actions. |
| Missing responsive coverage | Remove fixed 850px page width; wrap desktop/tablet controls and stack panes at <=760px. Keep source-code scrolling scoped to its editor/dialog. | Fresh 1024px and 390px Grid captures; assert document width does not exceed viewport. This is sampled coverage, not every device. |

## Safety and remaining product limits

No backend, model, network policy, authentication or canonical saved workflow is changed by the UI corrections. Existing shared code/schema changes from the preceding instruction feature remain a separate product scope. Article-reading acceptance is not inferred from UI screenshots or a successful News click. UI captures use labelled synthetic templates, never private recording contents. Subsequent functional changes require recapture.

## Independent re-review R1–R4 (subsequent correction pass)

A separate reviewer session `ses_e8aa2985fffeb3iiXzdXhYF7bf` found four specific residual defects in the first correction pass; that review is retained rather than calling the first pass complete.

- **R1:** Remove two-line ellipsis and mid-word wrapping from full desktop names. Hide decorative category badges in overview to reserve name width. At very small scales, use explicit short topology labels (full names remain on the accessible node and inspector); do not pretend a whole workflow can display every detail at phone width.
- **R2:** Override existing inline route colors for the selected connection with a cyan 3.5px non-scaling stroke and glow. Native Grid checks must inspect the computed stroke/filter as well as selection/deletion behavior.
- **R3:** Refit when a narrow canvas changes width; include the loop return in fit bounds and remove the obstructive minimap at narrow widths. Assert every node fits, separately from page-overflow checks.
- **R4:** Move navigation help out of the graph viewport into a reserved wrapping 11px footer. Observe its changing height to keep the inspector inside the available center pane after narrow-mode overview text appears. Assert the help cannot cover the graph.

Every subsequent functional edit requires recapturing the affected components and repeating the independent review; first-pass screenshots are comparison only.
