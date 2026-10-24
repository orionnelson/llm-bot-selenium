import { describe, expect, it, vi } from 'vitest';
import { uid } from './workflow';
import { template, linkNodes, makeRun, atTime, validateFlow } from './sre';
import { useStudio } from './store';
import { saveArtifacts, buildDAG, fromDAG } from './dag';
describe('node connections',()=>{
 it('adds a visible graph edge that survives JSON save/load and undo/redo',()=>{
  const w=template();w.edges=[];useStudio.setState({workflow:w,past:[],future:[]});
  useStudio.getState().change(linkNodes(w,'start','check-lambda'));
  const updated=useStudio.getState().workflow;
  expect(updated.edges).toHaveLength(1);expect(updated.edges[0]).toMatchObject({source:'start',target:'check-lambda'});
  expect(validateFlow(JSON.parse(JSON.stringify(updated))).edges).toEqual(updated.edges);
  useStudio.getState().undo();expect(useStudio.getState().workflow.edges).toHaveLength(0);
  useStudio.getState().redo();expect(useStudio.getState().workflow.edges).toHaveLength(1);
 });
 it('allows replacement wiring in the draft but blocks saving and execution until the old edge is deleted',()=>{
  const w=template(),draft=linkNodes(w,'start','summary');
  useStudio.setState({workflow:w,past:[],future:[]});useStudio.getState().change(draft);
  expect(useStudio.getState().workflow.edges).toHaveLength(w.edges.length+1);
  expect(()=>saveArtifacts(draft)).toThrow('multiple connections');
  expect(()=>buildDAG(draft)).toThrow('multiple connections');
  expect(()=>makeRun(draft,'errors')).toThrow('multiple connections');
  const repaired={...draft,edges:draft.edges.filter(e=>!(e.source==='start'&&e.target==='check-lambda'))};
  useStudio.getState().change(repaired);
  expect(saveArtifacts(useStudio.getState().workflow).python).toContain('dag = DAG(');
  useStudio.getState().undo();expect(()=>saveArtifacts(useStudio.getState().workflow)).toThrow('multiple connections');
  useStudio.getState().redo();expect(saveArtifacts(useStudio.getState().workflow).dagError).toBe('');
 });
 it('checks each branch separately at save time',()=>{
  const w=template();expect(()=>saveArtifacts(w)).not.toThrow();
  const draft=linkNodes(w,'check-errors','end','yes');
  expect(()=>saveArtifacts(draft)).toThrow('multiple connections');
  expect(saveArtifacts({...draft,edges:draft.edges.filter(e=>!(e.source==='check-errors'&&e.target==='query-logs'))}).dagError).toBe('');
 });
 it('follows a newly connected node during demo execution',()=>{const w=template();w.edges=w.edges.filter(e=>e.source!=='start');const linked=linkNodes(w,'start','summary');const r=makeRun(linked,'errors');expect(atTime(r,r.duration).states.summary).toBe('success');expect(atTime(r,r.duration).states['check-lambda']).toBe('skipped');});
 it('supports separately labelled yes/no condition ports',()=>{const w=template();w.edges=[];const a=linkNodes(w,'check-errors','query-logs','yes');const b=linkNodes(a,'check-errors','summary','no');expect(b.edges.map(e=>[e.sourceHandle,e.label])).toEqual([['yes','YES'],['no','NO']]);});
 it('rejects duplicate links, self links, nonexistent endpoints, cycles and wrong-direction ports',()=>{const w=template();expect(()=>linkNodes(w,'start','check-lambda')).toThrow('already linked');expect(()=>linkNodes(w,'summary','summary')).toThrow('itself');expect(()=>linkNodes(w,'missing','summary')).toThrow('existing');expect(()=>linkNodes(w,'query-logs','check-lambda')).toThrow('Cycles');expect(()=>linkNodes(w,'end','summary')).toThrow('no output');expect(()=>linkNodes(w,'summary','start')).toThrow('no input');expect(()=>linkNodes(w,'check-errors','summary','invalid')).toThrow('branch');});
 it('creates node and edge IDs on plain HTTP where crypto.randomUUID is absent',()=>{const original=globalThis.crypto;vi.stubGlobal('crypto',{getRandomValues:original.getRandomValues.bind(original)});try{expect(uid('node')).toMatch(/^node_[a-f0-9]{32}$/);const w=template();w.edges=[];expect(linkNodes(w,'start','summary').edges[0].id).toMatch(/^edge_[a-f0-9]{32}$/);}finally{vi.unstubAllGlobals();}});
});

it('preserves all Parallel outputs through save, DAG export/import, deletion and undo',()=>{
 const w=template();w.nodes.find(n=>n.id==='check-lambda')!.data.action='parallel';
 const draft=linkNodes(linkNodes(w,'check-lambda','summary'),'check-lambda','end');
 expect(saveArtifacts(draft).dagError).toBe('');
 const demo=makeRun(draft,'errors');expect(demo.status).toBe('Pending');expect(demo.events.some(e=>e.message.includes('concurrent execution adapter pending'))).toBe(true);
 const dag=buildDAG(draft),fork=dag.tasks.find(t=>t.task_id==='check-lambda')!;
 expect(fork.routes).toEqual({'branch:check-errors':'check-errors','branch:summary':'summary','branch:end':'end'});
 const copy=fromDAG(dag);const normalize=(d:ReturnType<typeof buildDAG>)=>({...d,tasks:d.tasks.map(t=>({...t,depends_on:[...t.depends_on].sort()}))});expect(normalize(buildDAG(copy))).toEqual(normalize(dag));
 expect(()=>linkNodes(draft,'check-lambda','summary')).toThrow('already linked');
 useStudio.setState({workflow:draft,past:[],future:[]});
 useStudio.getState().change({...draft,edges:draft.edges.filter(e=>!(e.source==='check-lambda'&&e.target==='summary'))});
 expect(Object.values(buildDAG(useStudio.getState().workflow).tasks.find(t=>t.task_id==='check-lambda')!.routes)).toHaveLength(2);
 useStudio.getState().undo();expect(saveArtifacts(useStudio.getState().workflow).dagError).toBe('');
 w.nodes.find(n=>n.id==='check-lambda')!.data.action='lambda';
 expect(()=>saveArtifacts({...draft,nodes:w.nodes})).toThrow('multiple connections');
});
