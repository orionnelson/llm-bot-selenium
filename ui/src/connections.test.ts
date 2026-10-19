import { describe, expect, it, vi } from 'vitest';
import { uid } from './workflow';
import { template, linkNodes, makeRun, atTime, validateFlow } from './sre';
import { useStudio } from './store';
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
 it('follows a newly connected node during demo execution',()=>{const w=template();w.edges=w.edges.filter(e=>e.source!=='start');const linked=linkNodes(w,'start','summary');const r=makeRun(linked,'errors');expect(atTime(r,r.duration).states.summary).toBe('success');expect(atTime(r,r.duration).states['check-lambda']).toBe('skipped');});
 it('supports separately labelled yes/no condition ports',()=>{const w=template();w.edges=[];const a=linkNodes(w,'check-errors','query-logs','yes');const b=linkNodes(a,'check-errors','summary','no');expect(b.edges.map(e=>[e.sourceHandle,e.label])).toEqual([['yes','YES'],['no','NO']]);});
 it('rejects duplicate links, self links, nonexistent endpoints, cycles and wrong-direction ports',()=>{const w=template();expect(()=>linkNodes(w,'start','check-lambda')).toThrow('already linked');expect(()=>linkNodes(w,'summary','summary')).toThrow('itself');expect(()=>linkNodes(w,'missing','summary')).toThrow('existing');expect(()=>linkNodes(w,'query-logs','check-lambda')).toThrow('Cycles');expect(()=>linkNodes(w,'end','summary')).toThrow('no output');expect(()=>linkNodes(w,'summary','start')).toThrow('no input');expect(()=>linkNodes(w,'check-errors','summary','invalid')).toThrow('branch');});
 it('creates node and edge IDs on plain HTTP where crypto.randomUUID is absent',()=>{const original=globalThis.crypto;vi.stubGlobal('crypto',{getRandomValues:original.getRandomValues.bind(original)});try{expect(uid('node')).toMatch(/^node_[a-f0-9]{32}$/);const w=template();w.edges=[];expect(linkNodes(w,'start','summary').edges[0].id).toMatch(/^edge_[a-f0-9]{32}$/);}finally{vi.unstubAllGlobals();}});
});
