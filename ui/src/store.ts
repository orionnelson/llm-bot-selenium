import { appendCapture, type Capture } from './recording';
import { create } from 'zustand';
import { template, validateFlow, type Workflow, type Run } from './sre';
interface State { capture?:Capture; workflow:Workflow; past:Workflow[]; future:Workflow[]; selected:string; run?:Run; clock:number; playing:boolean; speed:number; mode:'Demo'|'Replay'; history:Run[]; notice:string; change:(w:Workflow)=>void; select:(id:string)=>void; seek:(ms:number)=>void; undo:()=>void; redo:()=>void }
export const useStudio=create<State>((set,get)=>({workflow:template(),past:[],future:[],selected:'check-lambda',clock:0,playing:false,speed:1,mode:'Demo',history:[],notice:'Demo template · no infrastructure actions or browser session connected',
 change:(w)=>{try{const valid=validateFlow(w);set(s=>({workflow:valid,past:[...s.past.slice(-29),s.workflow],future:[],capture:appendCapture(s.capture,{type:'workflow.changed',nodes:valid.nodes.length,edges:valid.edges.length})}));}catch(e){set({notice:String(e)});}},select:(selected)=>set(s=>({selected,capture:appendCapture(s.capture,{type:'node.selected',nodeId:selected})})),seek:(clock)=>set({clock:Math.max(0,Math.min(get().run?.duration??0,clock)),playing:false}),
 undo:()=>{const s=get();if(s.past.length)set({workflow:s.past.at(-1)!,past:s.past.slice(0,-1),future:[s.workflow,...s.future]});},redo:()=>{const s=get();if(s.future.length)set({workflow:s.future[0],past:[...s.past,s.workflow],future:s.future.slice(1)});}
}));
