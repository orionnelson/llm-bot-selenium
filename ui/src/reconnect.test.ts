import { expect,it } from 'vitest';
import { template } from './sre';
import { reconnectInput } from './reconnect';
import { useStudio } from './store';
it('disconnects only the grabbed incoming edge with undo and redo',()=>{
 const w=template(),edge=w.edges[0];useStudio.setState({workflow:w,past:[],future:[]});
 useStudio.getState().change(reconnectInput(w,edge.id,null));
 expect(useStudio.getState().workflow.edges).toEqual(w.edges.slice(1));
 useStudio.getState().undo();expect(useStudio.getState().workflow).toEqual(w);
 useStudio.getState().redo();expect(useStudio.getState().workflow.edges).not.toContainEqual(edge);
});
it('moves the input atomically and preserves its edge identity and branch',()=>{
 const w=template(),edge=w.edges.find(e=>e.source==='check-errors'&&e.sourceHandle==='yes')!;
 const next=reconnectInput(w,edge.id,{source:edge.source,sourceHandle:edge.sourceHandle??null,target:'end',targetHandle:null});
 expect(next.edges).toHaveLength(w.edges.length);expect(next.edges.find(e=>e.id===edge.id)).toMatchObject({source:edge.source,target:'end',sourceHandle:'yes'});
 expect(w.edges.find(e=>e.id===edge.id)).toEqual(edge);
});
it('keeps the original graph on invalid or wrong-end drops',()=>{
 const w=template(),before=structuredClone(w),edge=w.edges[0];
 for(const target of ['start','missing'])expect(()=>reconnectInput(w,edge.id,{source:edge.source,sourceHandle:null,target,targetHandle:null})).toThrow();
 expect(()=>reconnectInput(w,edge.id,{source:'summary',sourceHandle:null,target:'end',targetHandle:null})).toThrow('Only the input');
 expect(w).toEqual(before);expect(()=>reconnectInput(w,'missing',null)).toThrow('no longer exists');
});
