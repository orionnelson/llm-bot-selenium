import { describe, expect, it } from 'vitest';
import fixture from '../../shared/synthetic.workflow.json';
import cases from '../../shared/url-cases.json';
import { addParallel, createSeed, parseWorkflow, portable, safeUrl, serialize, topological, validate, type Workflow } from './workflow';

const fresh = () => validate(structuredClone(fixture));
describe('v1 cross-runtime interchange', () => {
  it('roundtrips the shared synthetic manifest and orders the timeline', () => {
    expect(parseWorkflow(serialize(fresh()))).toEqual(fixture);
    expect(topological(fresh()).map(n => n.id)).toEqual(['page', 'enter', 'results']);
  });
  for (const c of cases.seeds) it(`preserves templates and discards query data: ${c.url}`, () => {
    const flow = createSeed(c.url);
    expect(Object.keys(flow.page.parameters).sort()).toEqual(c.parameters);
    expect(serialize(flow)).not.toContain(c.absent);
    expect(Object.values(flow.page.parameters).every(v => v === '')).toBe(true);
  });
  for (const url of cases.unsafe) it(`rejects unsafe URL: ${url}`, () => expect(() => safeUrl(url)).toThrow());
  it('redacts signed query data in page seeds and rejects signed parameter bindings', () => {
    const flow = createSeed('https://example.com/?signature=private&service={service}');
    expect(serialize(flow)).not.toContain('private');
    expect(flow.page.parameters).toEqual({ service: '' });
    expect(() => createSeed('https://example.com/{signature}')).toThrow('Sensitive parameter');
  });
  it('has honest proposal provenance and strips values at persistence boundary', () => {
    const flow = fresh();
    expect(flow.nodes[1]).toMatchObject({ provenance: 'model-proposed', review: 'pending', origin: 'offline-template' });
    expect(portable(flow).page.parameters).toEqual({ xyz: '', region: '' });
    expect(flow.page.parameters.xyz).toBe('synthetic search');
    flow.nodes[1].review = 'approved';
    expect(() => validate(flow)).toThrow(/pending/);
  });
});

describe('untrusted parser and graph contracts', () => {
  const invalid: [string, (f: Workflow) => void][] = [
    ['duplicate ID', f => { f.nodes.push(structuredClone(f.nodes[0])); }],
    ['missing edge endpoint', f => { f.edges[0].target = 'missing'; }],
    ['self-loop', f => { f.edges[0].target = f.edges[0].source; }],
    ['cycle', f => { f.edges.push({ id: 'back', source: 'results', target: 'page' }); }],
    ['duplicate connection', f => { f.edges.push({ ...f.edges[0], id: 'duplicate' }); }],
    ['edge/node ID collision', f => { f.edges[0].id = f.nodes[0].id; }],
    ['unstructured branch', f => { f.edges.push({ id: 'branch', source: 'page', target: 'results' }); }],
    ['missing page parameter', f => { delete f.page.parameters.xyz; }],
    ['missing binding', f => { f.nodes[1].bindings.query = 'missing'; }],
    ['required action binding', f => { f.nodes[1].action!.target = '{missing}'; }],
    ['sensitive parameter', f => { f.page.parameters.access_token = 'hidden'; }],
    ['literal query import', f => { f.page.urlTemplate = 'https://example.com?query=private'; }],
    ['credential URL in prompt', f => { f.nodes[1].prompt = 'Go to https://u:p@example.com'; }],
    ['secret in prompt', f => { f.nodes[1].prompt = 'token=hidden'; }],
    ['oversized graph', f => { f.nodes = Array.from({ length: 101 }, (_, i) => ({ ...structuredClone(f.nodes[0]), id: `node_${i}` })); }],
  ];
  for (const [label, mutate] of invalid) it(`rejects ${label} before render`, () => {
    const flow = fresh(); mutate(flow);
    expect(() => parseWorkflow(JSON.stringify(flow))).toThrow();
  });
  it('requires closed, paired parallel regions', () => {
    const flow = addParallel(fresh());
    expect(validate(flow)).toEqual(flow);
    const broken = structuredClone(flow);
    broken.edges.pop();
    expect(() => validate(broken)).toThrow();
    const badPair = structuredClone(flow);
    badPair.nodes.find(n => n.kind === 'fork')!.pairId = 'page';
    expect(() => validate(badPair)).toThrow(/paired/);
  });
  it('rejects early branch merges and external entry', () => {
    const flow = addParallel(fresh());
    const fork = flow.nodes.find(n => n.kind === 'fork')!;
    const join = flow.nodes.find(n => n.kind === 'join')!;
    const branches = flow.edges.filter(e => e.source === fork.id).map(e => e.target);
    flow.edges.push({ id: 'external', source: 'results', target: join.id });
    expect(() => validate(flow)).toThrow(/External/);
    flow.edges.pop();
    flow.edges.push({ id: 'early_merge', source: branches[0], target: branches[1] });
    expect(() => validate(flow)).toThrow();
  });
  for (const raw of ['null', '[]', '{', '{"version":"future"}', ' '.repeat(1_000_001)]) it('rejects malformed, unknown or oversized JSON', () => expect(() => parseWorkflow(raw)).toThrow());
  it('rejects unknown fields and prototype-shaped parameter keys', () => {
    expect(() => parseWorkflow(JSON.stringify({ ...fresh(), recording: 'not allowed' }))).toThrow();
    const flow = fresh(); flow.page.parameters = JSON.parse('{"__proto__":"no","xyz":"","region":""}');
    expect(() => validate(flow)).toThrow();
  });
});
