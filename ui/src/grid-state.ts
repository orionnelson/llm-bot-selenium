import { create } from 'zustand';
import { activeRun, browserHistory, browserRun, type BrowserRun } from './browser';
export interface GridStatus {grid:{ready:boolean;status:string;nodes?:number;browsers?:string[];edgeAvailable?:boolean};modelBusy:boolean;approvedUrls:string[];videoAvailable:boolean}
export async function gridStatus():Promise<GridStatus>{
 const response=await fetch('/api/test/status',{cache:'no-store',signal:AbortSignal.timeout(10000)});
 if(!response.ok)throw Error(`Grid backend unavailable (${response.status}). Serve this UI from the Python test backend; the static template host has no browser API.`);
 const value=await response.json();
 if(value.mode!=='test'||typeof value.grid?.ready!=='boolean'||!Array.isArray(value.approvedUrls)||!value.approvedUrls.every((u:unknown)=>typeof u==='string'))throw Error('Invalid Grid backend response');
 return value;
}
interface GridState {view:'grid'|'demo';run?:BrowserRun;history:BrowserRun[];status?:GridStatus;error:string;setRun:(run:BrowserRun)=>void;refresh:()=>Promise<void>;open:(id:string)=>Promise<void>}
export const useGrid=create<GridState>((set)=>({view:'grid',history:[],error:'',
 setRun:(run)=>set(s=>({view:'grid',run,history:[run,...s.history.filter(r=>r.id!==run.id)].slice(0,20)})),
 refresh:async()=>{try{const [status,history]=await Promise.all([gridStatus(),browserHistory()]);set(s=>({status,history,error:'',run:s.run?history.find(r=>r.id===s.run!.id)??s.run:history.find(activeRun)}));}catch(e){set({status:undefined,error:String(e)});}},
 open:async(id)=>{try{const run=await browserRun(id);set({view:'grid',run,error:''});}catch(e){set({error:String(e)});}},
}));
