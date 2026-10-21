import { useEffect, useRef, useState } from 'react';
import { loadDAG } from './backend';
import type { TaskSpec } from './dag';
import { activeRun, browserHistory, browserRun, cancelBrowserRun, recordingAsset, startBrowserRun, type BrowserRun } from './browser';
function download(value:unknown,name:string){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();URL.revokeObjectURL(url);}
export default function BrowserRunner({nodeId}:{nodeId:string}){
 const [saved,setSaved]=useState<{task:TaskSpec;revision:string}>(),[consent,setConsent]=useState(false),[video,setVideo]=useState(false),[run,setRun]=useState<BrowserRun>(),[history,setHistory]=useState<BrowserRun[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false),[selected,setSelected]=useState(0);
 const player=useRef<HTMLVideoElement>(null),latestNode=useRef(nodeId);latestNode.current=nodeId;
 async function policy(){setSaved(undefined);setConsent(false);setError('');try{const d=await loadDAG();if(latestNode.current!==nodeId)return;const task=d.definition.tasks.find(t=>t.task_id===nodeId);if(!task?.params.browser)throw Error('Select a saved browser task with an explicit policy. See examples/browser_dag.py.');setConsent(false);setSaved({task,revision:d.revision});}catch(e){setError(String(e));}}
 useEffect(()=>{let alive=true;setSaved(undefined);setConsent(false);setError('');loadDAG().then(d=>{if(!alive)return;const task=d.definition.tasks.find(t=>t.task_id===nodeId);if(!task?.params.browser)throw Error('Select a saved browser task with an explicit policy.');setConsent(false);setSaved({task,revision:d.revision});}).catch(e=>{if(alive)setError(String(e));});return()=>{alive=false;};},[nodeId]);
 useEffect(()=>{browserHistory().then(setHistory).catch(()=>{});},[]);
 useEffect(()=>{if(!run||!activeRun(run))return;let alive=true,timer:ReturnType<typeof setTimeout>;const poll=async()=>{try{const next=await browserRun(run.id);if(!alive)return;setRun(next);setHistory(h=>[next,...h.filter(r=>r.id!==next.id)].slice(0,20));if(activeRun(next))timer=setTimeout(poll,1000);else browserHistory().then(setHistory).catch(()=>{});}catch(e){if(alive){setError(String(e));timer=setTimeout(poll,3000);}}};timer=setTimeout(poll,500);return()=>{alive=false;clearTimeout(timer);};},[run?.id]);
 async function start(){if(!saved)return;setBusy(true);setError('');try{const id=await startBrowserRun(saved.task.task_id,saved.revision,consent,video);const next=await browserRun(id);setRun(next);setHistory(h=>[next,...h.filter(r=>r.id!==next.id)].slice(0,20));setSelected(0);}catch(e){setError(String(e));}finally{setBusy(false);}}
 async function cancel(){if(!run)return;try{await cancelBrowserRun(run.id);setRun(await browserRun(run.id));}catch(e){setError(String(e));}}
 function choose(index:number){setSelected(index);if(player.current&&player.current.readyState>=1&&run?.steps[index])player.current.currentTime=run.steps[index].videoMs/1000;}
 const step=run?.steps[selected],image=step?.after??step?.before??run?.frames[0];
 return <div className="browser-runner"><h3>Run &amp; Record · separate Grid browser</h3><p>Saved DAG → approved URL → page-grounded LLM choice → guarded Selenium action → private recording. No generated Python executes.</p>
 <button onClick={policy}>Reload saved policy</button>{saved&&<><p><b>{saved.task.label}</b><br/><code>{String(saved.task.params.target)}</code></p><p>{String(saved.task.params.prompt)}</p><details><summary>Approved controls and expected visible evidence</summary><pre>{JSON.stringify(saved.task.params.browser,null,2)}</pre></details></>}
 <label><input type="checkbox" disabled={!saved||busy} checked={consent} onChange={e=>setConsent(e.target.checked)}/>I approve this saved test URL, allowlisted read-only clicks, sending the marked visible region to local Qwen, and private screenshot/action recording. Synthetic data only.</label>
 <label><input type="checkbox" checked={video} onChange={e=>setVideo(e.target.checked)}/>Export an action-frame WebM replay (not continuous video; requires ffmpeg).</label>
 <div className="python-buttons"><button disabled={!saved||!consent||busy||!!(run&&activeRun(run))} onClick={start}>{busy?'Starting…':'Run approved saved task'}</button><button disabled={!run||!activeRun(run)} onClick={cancel}>Cancel browser run</button></div>
 <p className="muted">Closing this panel does not cancel the bounded run. Cancel prevents subsequent actions; an in-flight model request may finish before browser cleanup.</p>{error&&<p role="alert" className="red">{error}</p>}
 {run&&<section><h4>{run.status.toUpperCase()} · {run.taskId}</h4><p>{run.evidenceKind} · {run.modelCalls} model attempts · {run.frames.length} captured frames</p>{run.error&&<p className="red">{run.reason??run.error} · no successful result claimed</p>}{run.verifiedResult&&<p>Visible assertion: <b>{run.verifiedResult}</b></p>}
 <div className="python-buttons">{run.steps.map((s,i)=><button key={s.id} aria-pressed={selected===i} onClick={()=>choose(i)}>{i+1}. {s.label} · {s.state}</button>)}</div>
 {image?<img className="browser-run-frame" src={recordingAsset(image)} alt={`Recorded approved region for ${step?.label??'navigation'}`}/>:<p>No captured frame available. No screenshot is fabricated.</p>}
 {step&&<pre>{JSON.stringify({action:step.action,locator:step.locator,evidence:step.evidence,state:step.state},null,2)}</pre>}
 {run.video&&<><p>Action-frame replay · one second per captured frame, not wall-clock screen video.</p><video ref={player} className="browser-run-frame" controls src={recordingAsset(run.video.url)}/></>}
 <div className="python-buttons"><button disabled={activeRun(run)} onClick={()=>download(run,run.id+'-recording.json')}>Export recording</button><button disabled={activeRun(run)||!run.triage.events.length} onClick={()=>download(run.triage,run.id+'-triage.json')}>Export reusable triage session</button></div></section>}
 <h4>Private recordings</h4>{history.map(r=><button key={r.id} onClick={()=>{setRun(r);setSelected(0);}}>{r.startedAt} · {r.taskId} · {r.status}</button>)}
 </div>;
}
