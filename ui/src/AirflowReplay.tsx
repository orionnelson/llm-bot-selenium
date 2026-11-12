import { useEffect, useState } from 'react';
import { loadDAG } from './backend';
import { buildDAG, fromDAG } from './dag';
import type { Workflow } from './sre';

type Artifact = {id:string; revision:string; tasks:string[]; createdAt:number};
type State = {state:string; runId?:string; revision?:string; stopRequested?:boolean; tasks?:{task_id:string;state:string}[]; steps?:{task:string;step:number;state:string;reason?:string}[]};
async function api(path:string, body?:unknown, revision?:string){
 const response=await fetch('/api/airflow/artifacts'+path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json',...(revision?{'If-Match':revision}:{})},...(body?{body:JSON.stringify(body)}:{})});
 const value=await response.json();if(!response.ok)throw Error(value.error||'Replay request failed');return value;
}
export default function AirflowReplay({workflow,runIds}:{workflow:Workflow;runIds:string[]}){
 const [artifacts,setArtifacts]=useState<Artifact[]>([]),[selected,setSelected]=useState(''),[approval,setApproval]=useState<{key:string;revision:string}|null>(null),[synthetic,setSynthetic]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[configured,setConfigured]=useState(false),[state,setState]=useState<State>(),[logs,setLogs]=useState<string[]>([]);
 const reviewKey=JSON.stringify([workflow,runIds]);
 const reviewed=approval?.key===reviewKey;
 useEffect(()=>{setApproval(null);setSynthetic(false);},[reviewKey]);
 async function listing(){const value=await api('');setConfigured(value.configured===true);setArtifacts(value.artifacts);if(value.active){setSelected(value.active.artifactId);setState(value.active);}}
 useEffect(()=>{listing().catch(e=>setError(String(e)));},[]);
 async function action(fn:()=>Promise<void>){setBusy(true);setError('');try{await fn();}catch(e){setError(String(e));}finally{setBusy(false);}}
 async function save(){
  const saved=await loadDAG();
  if(JSON.stringify(buildDAG(workflow))!==JSON.stringify(buildDAG(fromDAG(saved.definition))))throw Error('Save the current DAG before reviewing its immutable replay snapshot.');
  if(!reviewed||!synthetic||approval?.revision!==saved.revision){setApproval(null);throw Error('Snapshot changed; review and approve this revision again.');}
  const value=await api('',{runIds,reviewed,synthetic},saved.revision);await listing();setSelected(value.id);setState(undefined);setApproval(null);setSynthetic(false);
 }
 async function refresh(){setState(await api('/'+selected+'/status'));setLogs((await api('/'+selected+'/logs')).logs);}
 const artifact=artifacts.find(a=>a.id===selected);
 return <section aria-label="Airflow fast replay">
  <h4>Airflow · deterministic fast replay</h4>
  <p>{configured?'Server configured. Ordinary replay uses no model and never reloads the current draft.':'Disabled / not configured. Server operator must enable Airflow replay.'}</p>
  <label><input type="checkbox" checked={reviewed} onChange={e=>{if(!e.target.checked)setApproval(null);else action(async()=>{const saved=await loadDAG();setApproval({key:reviewKey,revision:saved.revision});});}}/>I reviewed the saved serial DAG and selected recorded steps.</label>
  <label><input type="checkbox" checked={synthetic} onChange={e=>setSynthetic(e.target.checked)}/>I approve synthetic-only replay of this snapshot.</label>
  <button disabled={!configured||busy||!reviewed||!synthetic} onClick={()=>action(save)}>Save reviewed immutable artifact</button>
  <button disabled={busy} onClick={()=>action(listing)}>Refresh saved artifacts / configuration</button>
  <label>Saved artifact <select value={selected} disabled={busy} onChange={e=>{setSelected(e.target.value);setState(undefined);setLogs([]);}}><option value="">Select reviewed snapshot</option>{artifacts.map(a=><option key={a.id} value={a.id}>{a.id.slice(0,12)} · revision {a.revision.slice(0,12)}</option>)}</select></label>
  {artifact&&<><p>Immutable artifact: <code>{artifact.id}</code><br/>Reviewed snapshot revision: <code>{artifact.revision}</code><br/>Ordered canonical tasks: {artifact.tasks.join(' → ')}</p>
   <button disabled={busy||!!state&& !['idle','success','failed'].includes(state.state)} onClick={()=>action(async()=>{setState(await api('/'+selected+'/run',{confirmed:true}));})}>Run saved fast replay</button>
   <button disabled={busy} onClick={()=>action(refresh)}>Refresh status / tasks / results / logs</button>
   <button disabled={busy||!state||['idle','success','failed'].includes(state.state)} onClick={()=>action(async()=>{setState(await api('/'+selected+'/stop',{confirmed:true}));})}>{state?.state==='stopping'?'Retry stop request':'Stop replay safely'}</button>
  </>}
  {state&&<div role="status"><b>{state.state}{state.stopRequested?' · stop requested':''}</b>{state.runId&&<p>{state.runId}</p>}{state.state==='stopping'&&<p>Stop requested. Worker termination and Grid cleanup are pending; allow about 80 seconds after worker start. Refresh until Airflow confirms a terminal state.</p>}{state.tasks?.map(t=><p key={t.task_id}>{t.task_id}: {t.state}</p>)}{state.steps?.map((s,i)=><p key={i}>{s.task}/step-{s.step}: {s.state}{s.reason?` · ${s.reason}`:''}</p>)}</div>}
  {logs.length>0&&<pre>{logs.join('\n')}</pre>}
  <p>One Airflow task preserves the full ordered Selenium session. Stop uses a server-owned Airflow cancellation marker; terminal failed may mean stopped. Repair is a separate opt-in model/review workflow and requires a new saved artifact.</p>
  {error&&<p role="alert" className="red">{error}</p>}
 </section>;
}
