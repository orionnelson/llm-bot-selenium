import type { Connection } from '@xyflow/react';
import { linkNodes, type Workflow } from './sre';

// Invalid drops must never remove the original connection.
export function reconnectInput(w:Workflow,id:string,connection:Connection|null):Workflow {
 const edge=w.edges.find(e=>e.id===id);
 if(!edge)throw Error('Connection no longer exists');
 const draft={...w,edges:w.edges.filter(e=>e.id!==id)};
 if(!connection)return draft;
 if(connection.source!==edge.source||connection.sourceHandle!==(edge.sourceHandle??null))throw Error('Only the input end can be moved');
 const linked=linkNodes(draft,connection.source,connection.target,connection.sourceHandle,connection.targetHandle);
 return {...linked,edges:linked.edges.map(e=>e===linked.edges.at(-1)?{...edge,...e,id}:e)};
}
