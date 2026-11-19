import {forwardRef,useEffect,useImperativeHandle,useState} from 'react';
import {useGrid} from './grid-state';
import {activeRun,browserRun,cancelBrowserRun,parseRun,recordingAsset,type BrowserRun} from './browser';
import GridSessionView from './GridSessionView';
import {useJourneyDraft,or9Steps} from './journey-state';
import {useStudio} from './store';
import type {DAGSpec} from './dag';
export interface JourneyHandle {start:()=>Promise<void>;cancel:()=>Promise<void>}

export function JourneyInstructions(){
 const {steps,setSteps,setUrl}=useJourneyDraft(),run=useGrid(s=>s.run),busy=!!run&&activeRun(run);
 return <section className="journey-instructions" aria-label="Journey instructions"><header><b>What should the bot do?</b><span>One action per instruction · one DAG step</span></header>
 <div className="journey-examples"><button disabled={busy} onClick={()=>{setUrl('https://or9.ca/');setSteps([...or9Steps]);}}>or9.ca news example</button><button disabled={busy} onClick={()=>{setUrl('https://allenfort.ca/');setSteps(['Inspect the homepage and screenshot its title and main visible content.']);}}>allenfort.ca example</button></div>
 <ol>{steps.map((step,i)=><li key={i}><textarea aria-label={`Instruction ${i+1}`} disabled={busy} rows={2} maxLength={700} placeholder="One action: click News, read visible article excerpts, or screenshot content…" value={step} onChange={e=>setSteps(steps.map((s,j)=>j===i?e.target.value:s))}/><button aria-label={`Remove instruction ${i+1}`} disabled={busy||steps.length===1} onClick={()=>setSteps(steps.filter((_,j)=>i!==j))}>×</button></li>)}</ol>
 <button disabled={busy||steps.length>=8} onClick={()=>setSteps([...steps,''])}>+ Add step</button><small>Public browsing, scrolling, safe clicks and screenshots. No sign-ins, typing into page forms, purchases or submissions.</small></section>;
}

export async function startJourney(url:string,steps:string[]):Promise<{id:string;definition:DAGSpec}>{
 if(!/^https?:\/\//i.test(url.trim()))throw Error('Enter a full http:// or https:// URL.');
 if(!steps.length||steps.some(s=>!s.trim()))throw Error('Fill in each instruction before recording.');
 const response=await fetch('/api/browser/journeys',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url.trim(),steps:steps.map(s=>s.trim())}),signal:AbortSignal.timeout(15000)});
 const value=await response.json();if(!response.ok)throw Error(value.error||'Could not start browser journey');
 if(!/^[a-f0-9]{32}$/.test(value.id)||value.definition?.version!=='sre-dag/v1')throw Error('Invalid journey response');return value;
}

const JourneyRecorder=forwardRef<JourneyHandle,{onPlan:(definition:DAGSpec)=>void;notify:(text:string)=>void}>(function JourneyRecorder({onPlan,notify},ref){
 const draft=useJourneyDraft(),{run,history,setRun}=useGrid(),[busy,setBusy]=useState(false),[error,setError]=useState(''),[focusFrame,setFocusFrame]=useState<number|undefined>();
 const live=!!run&&activeRun(run);
 useEffect(()=>{void useGrid.getState().refresh();const id=setInterval(()=>void useGrid.getState().refresh(),10000);return()=>clearInterval(id);},[]);
 useEffect(()=>{if(!run||!activeRun(run))return;let alive=true,timer:ReturnType<typeof setTimeout>;
 const poll=async()=>{try{const next=await browserRun(run.id);if(alive){setRun(next);if(activeRun(next))timer=setTimeout(poll,700);}}catch(e){if(alive){setError(String(e));timer=setTimeout(poll,2000);}}};timer=setTimeout(poll,300);return()=>{alive=false;clearTimeout(timer);};},[run?.id]);
 useEffect(()=>{if(live)draft.seek(null);},[live,run?.id]);
 useEffect(()=>{if(run?.journey)onPlan(run.journey.definition);},[run?.id]);
 useEffect(()=>{if(live&&run?.steps.length)useStudio.getState().select(run.steps.at(-1)!.id);},[live,run?.id,run?.steps.length]);
 async function start(){if(busy||live)return;setBusy(true);setError('');try{const value=await startJourney(draft.url,draft.steps);setRun(await browserRun(value.id));draft.seek(null);notify('Recording started. Each instruction is a real browser DAG step.');}catch(e){setError(String(e));notify(String(e));}finally{setBusy(false);}}
 async function cancel(){if(run){await cancelBrowserRun(run.id);setRun(await browserRun(run.id));}}
 useImperativeHandle(ref,()=>({start,cancel}));
 function selectStep(id:string){useStudio.getState().select(id);const step=run?.steps.find(s=>s.id===id);if(!step||!run)return;const asset=step.after??step.before,index=run.frames.indexOf(asset);if(index>=0){setFocusFrame(index);draft.seek(run.frameTimesMs?.[index]??0);}}
 async function open(id:string){try{const value=await browserRun(id);setRun(value);if(value.journey){draft.setUrl(value.url);draft.setSteps(value.journey.instructions);}setFocusFrame(undefined);}catch(e){setError(String(e));}}
 const facts=run?.steps.flatMap(s=>s.facts??[])??[],uniqueFacts=facts.filter((f,i)=>facts.findIndex(v=>v.label===f.label)===i);
 return <section className="journey-recorder" aria-label="Browser session and DAG playback"><form className="journey-url" onSubmit={e=>{e.preventDefault();void start();}}><input aria-label="Session URL" placeholder="https://any-public-page.example/" type="url" maxLength={2048} required disabled={live||busy} value={live?(run?.currentUrl??draft.url):draft.url} onChange={e=>draft.setUrl(e.target.value)}/><button className="primary" disabled={live||busy} type="submit">{busy?'Opening…':'● Record'}</button>{live&&<button type="button" onClick={()=>void cancel().catch(e=>setError(String(e)))}>Stop</button>}</form>
 <header className="journey-session-status"><b>{run?(live?'LIVE SESSION':'SESSION REPLAY'):'Ready to record'}</b><span>{live?(run.status==='cancelling'?'Stopping after the current coder request…':run.phase==='thinking'?'Coder is planning the next action…':run.phase):run?.status??'Enter a URL, write steps, then Record'}</span>{history.length>0&&<select aria-label="Recorded sessions" disabled={live} value={run?.id??''} onChange={e=>void open(e.target.value)}><option value="" disabled>Recorded sessions</option>{history.map(r=><option key={r.id} value={r.id}>{new Date(r.startedAt).toLocaleTimeString()} · {new URL(r.url).hostname} · {r.status}</option>)}</select>}</header>
 {error&&<p role="alert" className="red">{error}</p>}{run?.error&&<p role="alert" className="red">{run.reason??run.error}</p>}
 {run?<><GridSessionView run={run} compact focusFrame={focusFrame} onFrame={ms=>draft.seek(live?null:ms)}/><ol className="journey-step-status" aria-label="DAG playback steps">{run.steps.map(step=><li key={step.id}><button onClick={()=>selectStep(step.id)}><span className={'step-dot '+step.state}>{step.state==='verified'?'✓':step.state==='running'?'●':step.state==='failed'?'!':'○'}</span>{step.label}</button>{step.result&&<small>{step.result}</small>}</li>)}</ol>
 {uniqueFacts.length>0&&<section className="journey-facts"><b>Observed article counts by source</b>{uniqueFacts.map(f=><p key={f.label}><span>{f.label}</span><strong>{f.count} articles</strong></p>)}<small>Counts read from the page, not inferred totals. Source-by-source screenshots are in the recording timeline.</small></section>}
 {run.steps.some(s=>s.generatedPython)&&<section className="journey-functions" aria-label="Generated browser functions"><h4>Generated functional code</h4><p>The local AI generates one restricted Python browser function per step. The controller validates its syntax, page evidence and public action, then interprets it through Selenium Grid—not unrestricted Python.</p>{run.steps.filter(s=>s.generatedPython).map(s=><details key={s.id}><summary>{s.label} · {s.state}</summary><pre>{s.generatedPython}</pre><p>Observed result: {s.result??'No verified result yet'}</p>{s.articles?.map((a,i)=><article key={i}><b>{a.title}</b><p>{a.text}</p><small>{a.url} · visible page excerpt, not a full linked-article read</small></article>)}</details>)}</section>}
 {run.steps.some(s=>s.screenshots?.length)&&<details><summary>Article-count screenshots</summary>{run.steps.flatMap(s=>s.screenshots??[]).map((shot,i)=><a key={i} href={recordingAsset(shot.url)} target="_blank" rel="noreferrer">{shot.label}: {shot.count} articles ↗</a>)}</details>}</>:<div className="journey-empty"><b>Your browser session appears here</b><p>Write the steps on the left. The bot uses the coder model to generate a page-grounded browser function for each action. Recordings replay alongside the DAG.</p></div>}
 </section>;
});
export default JourneyRecorder;
