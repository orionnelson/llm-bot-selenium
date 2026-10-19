import { VERSION, type Kind, type Workflow, type WorkflowNode } from '../../shared/workflow';
export { VERSION, type Kind, type Provenance, type Workflow, type WorkflowNode } from '../../shared/workflow';
export const MAX_BYTES = 1_000_000;
export const sensitive = /password|passwd|pwd|secret|token|auth|credential|signature|cookie|session|api.?key|access.?key|private.?key|^key$|^sid$|^jwt$|^code$/i;
const name = /^[A-Za-z_][A-Za-z0-9_]{0,63}$/;
const leak = /(?:password|passwd|pwd|secret|token|authorization|api[_-]?key|access[_-]?key|private[_-]?key|cookie|session|\bsid|\bjwt)\s*[=:]\s*(?!\[REDACTED\])\S+|bearer\s+\S+/i;
const reserved = new Set(['__proto__', 'constructor', 'prototype']);
function check(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}
function object(v: unknown, required: string[], optional: string[] = []): asserts v is Record<string, unknown> {
  check(v !== null && typeof v === 'object' && !Array.isArray(v), 'Expected object');
  const keys = Object.keys(v);
  check(required.every(k => keys.includes(k)) && keys.every(k => [...required, ...optional].includes(k)), 'Missing or unknown fields');
}
function id(v: unknown): asserts v is string {
  check(typeof v === 'string' && name.test(v) && !reserved.has(v), 'Invalid ID/name');
}
export function placeholders(text: string): string[] {
  const names = [...text.matchAll(/\{([A-Za-z_][A-Za-z0-9_]{0,63})\}/g)].map(m => m[1]);
  check(!/[{}]/.test(text.replace(/\{([A-Za-z_][A-Za-z0-9_]{0,63})\}/g, '')), 'Malformed placeholder');
  check(names.every(n => !sensitive.test(n)), 'Sensitive parameter name');
  return [...new Set(names)];
}
export function safeUrl(value: string, redact = false): string {
  check(typeof value === 'string' && value.length > 0 && value.length <= 8192, 'Invalid URL length');
  check(!/[\s\\\x00-\x1f\x7f]/.test(value), 'URL contains whitespace or backslash');
  check(/^https?:\/\/[^/?#]+/i.test(value), 'Only absolute HTTP(S) URLs are allowed');
  const url = new URL(value);
  check(['http:', 'https:'].includes(url.protocol) && url.hostname, 'Only absolute HTTP(S) URLs are allowed');
  check(!url.username && !url.password && !value.match(/^https?:\/\/[^/?#]*@/i), 'Credential URLs are forbidden');
  check(!url.port || Number(url.port) > 0, 'Invalid port');
  const authority = value.slice(value.indexOf('//') + 2).split(/[/?#]/)[0];
  check(!/[{}%]/.test(authority), 'Host placeholders/encoding are forbidden');
  check(!url.hash && !value.includes('#'), 'URL fragments are not stored; remove the fragment');
  const pairs: [string, string][] = [];
  for (const [key, original] of url.searchParams) {
    let item = original;
    if (sensitive.test(key)) {
      check(redact || item === '[REDACTED]', 'Sensitive query value must be redacted');
      item = '[REDACTED]';
    }
    pairs.push([key, item]);
  }
  check(!leak.test(decodeURIComponent(url.pathname)), 'Sensitive URL path');
  url.search = new URLSearchParams(pairs).toString();
  const normalized = url.toString().replace(/%7B/gi, '{').replace(/%7D/gi, '}').replace(/%5B/gi, '[').replace(/%5D/gi, ']');
  placeholders(decodeURIComponent(normalized));
  return normalized;
}
function text(v: unknown, max = 2000): asserts v is string {
  check(typeof v === 'string' && v.length <= max, 'Invalid or oversized text');
  check(!leak.test(v), 'Potential secret in text');
  for (const match of v.matchAll(/https?:\/\/[^\s<>"']+/g)) safeUrl(match[0]);
}
export function validate(value: unknown): Workflow {
  object(value, ['version', 'title', 'synthetic', 'page', 'nodes', 'edges']);
  check(value.version === VERSION, 'Unsupported workflow version');
  text(value.title, 160);
  check(typeof value.synthetic === 'boolean', 'synthetic must be boolean');
  const page = value.page;
  object(page, ['urlTemplate', 'parameters']);
  check(typeof page.urlTemplate === 'string', 'Invalid page URL');
  safeUrl(page.urlTemplate);
  for (const [key, item] of new URL(page.urlTemplate).searchParams) {
    check(sensitive.test(key) || placeholders(item).length > 0, 'Literal query values must be converted to parameters with Create seed');
  }
  const params = page.parameters;
  check(params && typeof params === 'object' && !Array.isArray(params) && Object.keys(params).length <= 64, 'Invalid parameters');
  for (const [key, item] of Object.entries(params)) {
    id(key); check(!sensitive.test(key), 'Sensitive parameter name'); text(item, 500);
  }
  check(placeholders(decodeURIComponent(page.urlTemplate)).every(k => Object.hasOwn(params, k)), 'Missing required page parameter');
  check(Array.isArray(value.nodes) && value.nodes.length > 0 && value.nodes.length <= 100, 'Graph must have 1–100 nodes');
  check(Array.isArray(value.edges) && value.edges.length <= 200, 'Graph exceeds 200 edges');
  const nodes = new Map<string, WorkflowNode>();
  for (const node of value.nodes) {
    object(node, ['id', 'kind', 'title', 'position', 'provenance', 'bindings'], ['pairId', 'prompt', 'action', 'review', 'origin', 'timestamp']);
    id(node.id); check(!nodes.has(node.id), 'Duplicate node ID');
    check(['page', 'action', 'segment', 'fork', 'join'].includes(node.kind as string), 'Invalid node kind');
    check(['observed', 'detected', 'model-proposed', 'approved', 'executed'].includes(node.provenance as string), 'Invalid provenance');
    text(node.title, 160);
    object(node.position, ['x', 'y']);
    check(Object.values(node.position).every(n => typeof n === 'number' && Number.isFinite(n) && Math.abs(n) <= 100000), 'Invalid position');
    check(node.bindings && typeof node.bindings === 'object' && !Array.isArray(node.bindings) && Object.keys(node.bindings).length <= 64, 'Invalid bindings');
    for (const [key, binding] of Object.entries(node.bindings)) {
      id(key); check(!sensitive.test(key) && typeof binding === 'string' && Object.hasOwn(params, binding), 'Missing or sensitive binding');
    }
    if ('prompt' in node) text(node.prompt);
    if ('action' in node) {
      object(node.action, ['verb', 'target']);
      check(['click', 'navigate', 'inspect', 'type'].includes(node.action.verb as string), 'Invalid semantic action');
      text(node.action.target, 500);
      check(placeholders(node.action.target).every(k => Object.hasOwn(node.bindings!, k)), 'Missing required action binding');
    }
    if (node.provenance === 'model-proposed') check(node.review === 'pending' && ['offline-template', 'user-authored', 'model'].includes(node.origin as string) && 'prompt' in node && 'action' in node, 'Proposal must be pending with prompt, candidate and origin');
    if ('review' in node) check(['pending', 'approved'].includes(node.review as string), 'Invalid review');
    if ('origin' in node) check(['offline-template', 'user-authored', 'model'].includes(node.origin as string), 'Invalid origin');
    if ('timestamp' in node) check(typeof node.timestamp === 'number' && Number.isFinite(node.timestamp) && node.timestamp >= 0 && node.timestamp <= 86400, 'Invalid timestamp');
    if (node.kind === 'fork' || node.kind === 'join') id(node.pairId);
    else check(!('pairId' in node), 'Only fork/join nodes have pairs');
    nodes.set(node.id, node as unknown as WorkflowNode);
  }
  const out = new Map([...nodes.keys()].map(k => [k, [] as string[]]));
  const incoming = new Map([...nodes.keys()].map(k => [k, [] as string[]]));
  const edgeIds = new Set<string>(), links = new Set<string>();
  for (const edge of value.edges) {
    object(edge, ['id', 'source', 'target']); id(edge.id);
    check(typeof edge.source === 'string' && typeof edge.target === 'string' && nodes.has(edge.source) && nodes.has(edge.target), 'Edge references missing node');
    const link = `${edge.source}:${edge.target}`;
    check(edge.source !== edge.target && !edgeIds.has(edge.id) && !nodes.has(edge.id) && !links.has(link), 'Self-loop or duplicate ID/edge');
    edgeIds.add(edge.id); links.add(link);
    out.get(edge.source)!.push(edge.target); incoming.get(edge.target)!.push(edge.source);
  }
  const degree = new Map([...incoming].map(([key, list]) => [key, list.length]));
  const pending = [...nodes.keys()].filter(k => !degree.get(k));
  let visited = 0;
  while (pending.length) {
    const key = pending.pop()!; visited++;
    for (const target of out.get(key)!) {
      degree.set(target, degree.get(target)! - 1);
      if (!degree.get(target)) pending.push(target);
    }
  }
  check(visited === nodes.size, 'Graph contains a cycle');
  for (const [key, node] of nodes) {
    check(incoming.get(key)!.length <= (node.kind === 'join' ? 200 : 1), 'Multiple inputs require a join');
    check(out.get(key)!.length <= (node.kind === 'fork' ? 200 : 1), 'Multiple outputs require a fork');
    if (node.kind === 'fork' || node.kind === 'join') {
      const pair = nodes.get(node.pairId!);
      check(pair?.kind === (node.kind === 'fork' ? 'join' : 'fork') && pair.pairId === key, 'Fork/join must be reciprocally paired');
      check((node.kind === 'fork' ? out : incoming).get(key)!.length >= 2, 'Fork/join needs at least two branches');
    }
    if (node.kind === 'fork') {
      const end = node.pairId!;
      const regions: Set<string>[] = [];
      for (const start of out.get(key)!) {
        const region = new Set<string>(), todo = [start];
        while (todo.length) {
          const current = todo.pop()!;
          if (current === end || region.has(current)) continue;
          region.add(current);
          check(out.get(current)!.length, 'Fork branch does not reach paired join');
          todo.push(...out.get(current)!);
        }
        check(regions.every(other => [...region].every(n => !other.has(n))), 'Fork branches merge before paired join');
        regions.push(region);
      }
      const region = new Set(regions.flatMap(r => [...r]));
      check([...region, end].every(dst => incoming.get(dst)!.every(src => src === key || region.has(src))), 'External edge enters parallel region');
    }
  }
  return value as unknown as Workflow;
}
export function parseWorkflow(raw: string): Workflow {
  check(new TextEncoder().encode(raw).length <= MAX_BYTES, 'Manifest exceeds 1 MB');
  return validate(JSON.parse(raw));
}
export function serialize(flow: Workflow): string { return JSON.stringify(validate(flow), null, 2); }
/** Persistence/export intentionally excludes even innocently named parameter values. */
export function portable(flow: Workflow): Workflow {
  return validate({ ...flow, page: { ...flow.page, parameters: Object.fromEntries(Object.keys(flow.page.parameters).map(k => [k, ''])) } });
}
// getRandomValues also works on the owner's plain-HTTP LAN host; randomUUID requires HTTPS.
export function uid(prefix: string): string { return `${prefix}_${Array.from(crypto.getRandomValues(new Uint8Array(16)), b => b.toString(16).padStart(2, '0')).join('')}`; }
export function createSeed(url: string): Workflow {
  const clean = new URL(safeUrl(url, true));
  const pairs: [string, string][] = [];
  for (const [key, value] of clean.searchParams) {
    if (sensitive.test(key)) pairs.push([key, '[REDACTED]']);
    else if (placeholders(value).length) pairs.push([key, value]);
    else { id(key); pairs.push([key, `{${key}}`]); }
  }
  clean.search = new URLSearchParams(pairs).toString();
  const urlTemplate = safeUrl(clean.toString());
  const parameters = Object.fromEntries(placeholders(decodeURIComponent(urlTemplate)).map(n => [n, '']));
  return validate({ version: VERSION, title: 'Offline page seed', synthetic: false,
    page: { urlTemplate, parameters }, nodes: [
      { id: 'page', kind: 'page', title: 'Page seed', position: { x: 60, y: 150 }, provenance: 'detected', bindings: Object.fromEntries(Object.keys(parameters).map(k => [k, k])) },
      { id: 'proposal', kind: 'action', title: 'Unverified candidate', position: { x: 380, y: 150 }, provenance: 'model-proposed', bindings: {}, prompt: 'Look for and click Enter', action: { verb: 'click', target: 'Enter' }, review: 'pending', origin: 'offline-template' },
    ], edges: [{ id: 'page_proposal', source: 'page', target: 'proposal' }] });
}
export function topological(flow: Workflow): WorkflowNode[] {
  const result: WorkflowNode[] = [], done = new Set<string>();
  while (result.length < flow.nodes.length) {
    const next = flow.nodes.find(n => !done.has(n.id) && flow.edges.filter(e => e.target === n.id).every(e => done.has(e.source)));
    if (!next) break;
    done.add(next.id); result.push(next);
  }
  return result;
}
export function addParallel(flow: Workflow, position = { x: 100, y: 360 }): Workflow {
  const fork = uid('fork'), join = uid('join'), a = uid('segment'), b = uid('segment');
  const make = (id: string, kind: Kind, title: string, x: number, y: number, pairId?: string): WorkflowNode => ({ id, kind, title, position: { x, y }, provenance: 'approved', bindings: {}, ...(pairId ? { pairId } : {}) });
  return validate({ ...flow, nodes: [...flow.nodes,
    make(fork, 'fork', 'Parallel fork', position.x, position.y, join),
    make(a, 'segment', 'Branch A · reusable segment', position.x + 270, position.y - 90),
    make(b, 'segment', 'Branch B · reusable segment', position.x + 270, position.y + 90),
    make(join, 'join', 'Join branches', position.x + 540, position.y, fork)],
    edges: [...flow.edges, ...[[fork, a], [fork, b], [a, join], [b, join]].map(([source, target]) => ({ id: uid('edge'), source, target }))] });
}
