import { createSeed, portable, serialize, validate } from './workflow';
import { config, validateFlow, type Workflow } from './sre';
import { validateSnippet } from './snippets';

/** Import only canonical offline seeds, not arbitrary older editor graphs whose actions would be lost. */
export function importPageSeed(value: unknown): Workflow {
  const seed = portable(validate(value));
  const expected = createSeed(seed.page.urlTemplate);
  if (serialize(seed) !== serialize(expected)) throw Error('Only unmodified offline page seeds can be imported; edited legacy graphs are not converted.');
  const snippet = validateSnippet({
    version: 1, id: 'offline-page', name: 'Offline page seed',
    urlTemplate: seed.page.urlTemplate, parameters: seed.page.parameters,
    source: { sessionId: 'offline-page-seed', mode: 'offline', provenance: 'offline-template', eventIds: [] },
    steps: [],
  });
  return validateFlow({
    version: 1, name: 'Offline page seed — browser pending', snippets: [snippet],
    nodes: [
      { id: 'start', type: 'action', position: { x: 20, y: 160 }, data: { action: 'start', label: 'Start', config: config() } },
      { id: 'page', type: 'action', position: { x: 220, y: 160 }, data: { action: 'snippet', label: 'Offline page seed — unverified', config: {
        ...config(snippet.urlTemplate), method: 'Browser', screenshot: false, metrics: [], region: '', retries: 0,
        prompt: 'Offline template only. Unverified intent: Look for and click Enter. No page detection, model inference or browser execution has occurred.', snippet,
      } } },
      { id: 'end', type: 'action', position: { x: 620, y: 160 }, data: { action: 'end', label: 'End', config: config() } },
    ],
    edges: [{ id: 'start-page', source: 'start', target: 'page' }, { id: 'page-end', source: 'page', target: 'end' }],
  });
}
