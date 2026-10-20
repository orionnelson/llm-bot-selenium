import { execFileSync, spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import cases from '../../shared/url-cases.json';
import { createSeed, parseWorkflow, portable, serialize } from './workflow';
import { importPageSeed } from './page-seed';
import { atTime, makeRun, validateFlow } from './sre';
import { buildDAG, fromDAG } from './dag';
import { validateSnippet } from './snippets';

const directories = [];
const script = resolve('scripts/seed-page.mjs');
function target() {
  const dir = mkdtempSync(join(tmpdir(), 'studio-seed-'));
  directories.push(dir);
  return join(dir, 'page.json');
}
function invoke(url, output) {
  return spawnSync(process.execPath, ['--experimental-strip-types', script, 'open', url, '--output', output], { encoding: 'utf8' });
}
afterEach(() => { for (const dir of directories.splice(0)) rmSync(dir, { recursive: true, force: true }); });

describe('offline page-seed CLI uses the actual editor contract', () => {
  for (const item of cases.seeds) it(`imports the exact portable editor seed: ${item.url}`, () => {
    const output = target();
    const result = invoke(item.url, output);
    expect(result.status, result.stderr).toBe(0);
    const raw = readFileSync(output, 'utf8');
    const flow = parseWorkflow(raw);
    expect(flow).toEqual(portable(createSeed(item.url)));
    expect(flow.page.parameters).toEqual(Object.fromEntries(item.parameters.map(k => [k, ''])));
    expect(raw).not.toContain(item.absent);
    expect(flow.nodes[1]).toMatchObject({ review: 'pending', origin: 'offline-template' });
    expect(result.stdout).toContain('No browser or model was invoked');
  });
  it('preserves path/query placeholders, redacts signatures and roundtrips saved JSON', () => {
    const output = target();
    const result = invoke('https://example.com/services/{service}?query={xyz}&signature=private-marker', output);
    expect(result.status, result.stderr).toBe(0);
    const flow = parseWorkflow(readFileSync(output, 'utf8'));
    expect(flow.page.parameters).toEqual({ service: '', xyz: '' });
    expect(flow.page.urlTemplate).toContain('signature=[REDACTED]');
    expect(serialize(flow)).not.toContain('private-marker');
    expect(parseWorkflow(serialize(flow))).toEqual(flow);
  });
  for (const url of [...cases.unsafe.filter(url => !url.includes('?token=')), 'https://example.com/?query={constructor}']) it(`fails closed without writing: ${url}`, () => {
    const output = target();
    const result = invoke(url, output);
    expect(result.status).toBe(2);
    expect(() => readFileSync(output)).toThrow();
    expect(result.stdout + result.stderr).not.toContain(url);
  });
  it('imports into the active SRE graph and reuses the offline snippet without fabricating execution', () => {
    const output = target();
    expect(invoke('https://example.com/{service}?query={xyz}&sid=private-marker', output).status).toBe(0);
    const workflow = importPageSeed(parseWorkflow(readFileSync(output, 'utf8')));
    expect(validateFlow(JSON.parse(JSON.stringify(workflow)))).toEqual(workflow);
    const snippet = workflow.snippets[0];
    expect(snippet.source).toMatchObject({ mode: 'offline', provenance: 'offline-template', eventIds: [] });
    expect(snippet.steps).toEqual([]);
    expect(snippet.parameters).toEqual({ service: '', xyz: '' });
    expect(JSON.stringify(workflow)).not.toContain('private-marker');
    expect(fromDAG(buildDAG(workflow)).nodes.find(n => n.id === 'page').data.config.snippet).toEqual(snippet);
    const run = makeRun(workflow, 'healthy');
    expect(run.status).toBe('Pending');
    expect(atTime(run, run.duration).states.page).toBe('waiting');
    expect(atTime(run, run.duration).states.end).toBe('skipped');
    expect(run.events.some(e => e.nodeId === 'page' && e.status === 'success')).toBe(false);
  });
  it('does not silently discard edited legacy graph actions or claim offline events were recorded', () => {
    const seed = createSeed('https://example.com/?q={term}');
    seed.nodes[1].prompt = 'Different user intent';
    expect(() => importPageSeed(seed)).toThrow('unmodified');
    const snippet = importPageSeed(createSeed('https://example.com/')).snippets[0];
    expect(() => validateSnippet({ ...snippet, source: { ...snippet.source, mode: 'recorded' } })).toThrow();
    expect(() => validateSnippet({ ...snippet, steps: [{ id: 'fake', elapsedMs: 0, action: 'navigate', url: 'https://example.com/' }], source: { ...snippet.source, eventIds: ['fake'] } })).toThrow();
  });
  it('never clobbers an existing file, even when validation succeeds', () => {
    const output = target();
    writeFileSync(output, 'keep this draft');
    expect(invoke('https://example.com/?query={xyz}', output).status).toBe(2);
    expect(readFileSync(output, 'utf8')).toBe('keep this draft');
  });
  it('does not navigate even an unreachable hostname', () => {
    const output = target();
    const result = invoke('https://page-seed.invalid/?query=private-marker', output);
    expect(result.status, result.stderr).toBe(0);
    expect(readFileSync(output, 'utf8')).not.toContain('private-marker');
  });
  it('rejects invalid arguments without echoing user data', () => {
    const result = spawnSync(process.execPath, ['--experimental-strip-types', script, 'open', '--private-marker=value'], { encoding: 'utf8' });
    expect(result.status).toBe(2);
    expect(result.stdout + result.stderr).not.toContain('private-marker');
    expect(execFileSync(process.execPath, ['--experimental-strip-types', script, '--help'], { encoding: 'utf8' })).toContain('open');
  });
});
