import { buildDAG, fromDAG, type DAGSpec, type LayoutSpec } from './dag';
import type { Workflow } from './sre';
export interface BackendDAG { definition:DAGSpec; revision:string; python:string; plan:{root:string[];bodies:Record<string,string[]>;execution:string} }
export async function loadDAG():Promise<BackendDAG> { return request(); }
export async function commitDAG(workflow:Workflow,revision:string):Promise<BackendDAG> {
 return request({method:'PUT',headers:{'Content-Type':'application/json','If-Match':revision},body:JSON.stringify(buildDAG(workflow))});
}
async function request(init?:RequestInit):Promise<BackendDAG> {
 const response=await fetch('/api/dag',{...init,cache:'no-store',signal:AbortSignal.timeout(10000)});
 if(!response.ok)throw Error(response.status===409?'Backend DAG changed. Load DAG before saving; local draft retained.':`DAG backend unavailable or rejected the definition (${response.status}); local draft retained.`);
 const value=await response.json();
 if(typeof value.revision!=='string'||typeof value.python!=='string'||!value.plan||value.plan.execution!=='not started')throw Error('Invalid DAG backend response');
 fromDAG(value.definition);return value;
}
export function projectDAG(value:BackendDAG,layout?:LayoutSpec):Workflow {return fromDAG(value.definition,layout);}

// React Flow measurements/selection are not author edits and must not block DAG loading.
export function draftKey(w:Workflow):string {return JSON.stringify([w.name,w.nodes.map(n=>({id:n.id,data:n.data,position:n.position})),w.edges.map(e=>({source:e.source,target:e.target,sourceHandle:e.sourceHandle??null,targetHandle:e.targetHandle??null})),w.snippets]);}
