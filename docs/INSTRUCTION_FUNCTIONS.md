# Instruction-driven browser functions

Enter a public URL, add one action per instruction, and Record. For example: find the Projects section, click Security News, then read the visible article headlines/excerpts. Each instruction becomes a node in an immutable recording DAG; it never overwrites the canonical saved workflow.

The local Qwen Coder generates a restricted function:

```python
def run(browser):
    browser.click("observed-candidate-id", "current-evidence-hash")
```

The controller parses the Python AST into exactly one allowlisted public-browser operation and performs it through Selenium Grid. It does **not** exec/eval Python or permit imports, loops, arbitrary attributes, system/filesystem access, form input or submissions. Click/scroll are bound to an observed control and fresh page evidence. `browser.read_articles(evidence)` returns visible, grounded headlines/excerpts, not invented counts or full linked article bodies. The ordinary arbitrary-Python inspector remains review/export-only.

The UI displays generated functional code, state, observed results and recording frames. Captures and outputs are evidence, not proof of unexecuted steps. Re-running a journey observes/regenerates against a fresh page; stale candidate IDs are not a reusable locator contract.

Public URL validation plus request/redirect interception rejects private/internal destinations and credential URLs. Existing capture masks, storage/action/time bounds, cancellation and session cleanup remain. The authenticated LAN proxy stays authenticated; no public-hosting/security setting is changed.

Actual public acceptance must be reported separately from unit/mock and rendered UI tests. or9.ca has previously exposed its controls behind an unready loader; do not force JS clicks, hide overlays or claim the news was read without verified visible text. Keep actual failed/malformed model attempts visible rather than relabeling them success.
