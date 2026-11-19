**No remaining concrete P1/P2 blockers found on fresh inspection of the two files. No production correction needed.**

- `ui/src/App.tsx:154`: Guard ordering now preserves existing Escape, Ctrl/Cmd+Enter, and Ctrl/Cmd+Z behavior on focused interactive controls, while Ctrl/Cmd+S retains its original placement. `defaultPrevented` remains first. The interactive guard still protects native Space activation and prevents unrelated global seeking; background demo Space and the canvas exclusion remain intact.
- `ui/src/keyboard-shortcuts.test.jsx:37–48`: The seek spies address the no-run clamping blind spot, and the handled-key matrix now includes ArrowLeft and End.
- `ui/src/keyboard-shortcuts.test.jsx:57–60`: The new regression covers focused-button Escape reaching App selection clearing and Ctrl+S reaching local persistence.

**Minor coverage limitation:** the Escape assertion verifies selection clearing, not actual modal dismissal; the production dismissal branch is nevertheless correctly before the interactive guard. The harness still mocks `closest`, so native activation and event propagation remain separately attributed browser/Grid evidence.

Read-only source review only; I did not execute tests or Grid captures.
