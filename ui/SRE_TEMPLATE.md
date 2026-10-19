# SRE Flow Builder template

Run `npm ci --include=dev`, `npm test`, `npm run dev` or `npm run build`.

An editable phase1/2 UI sandbox for llm-bot-selenium. No infrastructure execution or live remote browser is connected. All fixture observations, metrics and run traces are explicitly marked demonstration data.

## Try it

1. Select Check Lambda Page; change function/region/metrics in Node Config.
2. Choose Errors found, Healthy, Incident failure, Log-query retry or Approval waiting, then Run demo.
3. Pause, scrub or click logs: node statuses and outputs derive from the same recorded event stream. Select Outputs for values at that time.
4. Use Node state selector to preview all lifecycle states for the selected node.
5. Replay a run: the historical graph/config is read-only and independent of the editable draft. Edit draft returns to your current workflow.
6. Drag actions from palette, connect handles, move nodes, use automatic layout, right-click to duplicate/delete. Ctrl+S saves locally. Ctrl+Z / Ctrl+Shift+Z undo/redo.
7. JSON data edits the whole validated template; Export/Import move workflow definitions. Never include credentials. Save/load use this browser's localStorage, not a server account.
8. Drag splitters for sidebar, right pane and inspector. Layout persists locally. Templates tab reloads the base template; Reset clears execution only.

## State model

`sre.ts`: versioned graph, registry, strict bounded graph/config validation, deterministic graph traversal and append-only demo events. Conditions use configured source handles and fixed demo errors; no eval. Structured bounded for/while demo blocks are supported; generic parallel execution remains pending. See README.md for the newer control-flow, triage-snippet and splitter interfaces. Unsupported multi-output serial nodes reject simulation.
`store.ts`: editable workflow plus bounded undo/redo and common replay clock in Zustand.
`App.tsx`: unified graph, HTML browser fixture, debugger, inspector and history. ELK is loaded only for automatic layout.
`SeedStudio.tsx` preserves the preceding URL-seed/semantic-flow editor source; legacy shared IR validators and 38 tests remain untouched. It is not the default SRE view.

No real Network/Screenshots are fabricated. LLM tab shows only deterministic fixture observations and explicitly reports no LLM call. Schedule explains the backend gap. Share exports JSON rather than inventing public access.

## Hosting

The existing Swiss app's hosted and OpenCode files are backed up as `swiss-original.html`; its nested hurricane app is retained. `serve-template.ts` is a static Bun server on3001, not an execution API. OpenCode's embedded Bun can run it with `BUN_BE_BUN=1 /usr/local/bin/opencode serve-template.ts`. It has self-only CSP and no external fonts/telemetry. Process is not restart-managed by Kubernetes: an operator should add a managed static server deployment before relying on availability after a pod restart.

Actual Selenium transport, auth/RBAC, backend workflow persistence/events/workers, real SRE integrations, LLM calls, recordings and production scheduling are not implemented in this template. Browser screenshot acceptance is blocked if no supported browser is available; do not disable browser sandbox to force it.
