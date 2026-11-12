import { useState } from 'react';
import { loadDAG } from './backend';
import { buildDAG, fromDAG } from './dag';
import { browserHistory, exportStandalone, type BrowserRun } from './browser';
import type { Workflow } from './sre';
import AirflowReplay from './AirflowReplay';

export default function StandaloneExport({workflow,revision,runIds}:{workflow?:Workflow;revision?:string;runIds?:string[]}){
 const [error,setError]=useState(''),[busy,setBusy]=useState(false),[runs,setRuns]=useState<BrowserRun[]>([]),[chosen,setChosen]=useState<string[]>([]);
 async function sources(){setError('');try{setRuns((await browserHistory()).filter(r=>r.status==='passed'));}catch(e){setError(String(e));}}
 async function download(){setBusy(true);setError('');try{
  let expected=revision;
  if(workflow){const saved=await loadDAG();if(JSON.stringify(buildDAG(workflow))!==JSON.stringify(buildDAG(fromDAG(saved.definition))))throw Error('Save the current DAG before exporting; export uses only the canonical saved revision.');expected=saved.revision;}
  if(!expected)throw Error('Reload the saved DAG; a canonical revision is required.');
  const source=await exportStandalone(expected,runIds??chosen);
  const url=URL.createObjectURL(new Blob([source],{type:'text/x-python'}));const a=document.createElement('a');a.href=url;a.download='workflow_standalone.py';a.click();URL.revokeObjectURL(url);
 }catch(e){setError(String(e));}finally{setBusy(false);}}
 return <section aria-label="Standalone Selenium export"><button disabled={busy} onClick={download}>{busy?'Validating export…':'Export standalone Selenium .py'}</button>
 {workflow&&<><button onClick={sources}>Choose completed recorded runs</button>{runs.map(r=><label key={r.id}><input type="checkbox" checked={chosen.includes(r.id)} onChange={e=>setChosen(e.target.checked?[...chosen,r.id]:chosen.filter(id=>id!==r.id))}/>{r.taskId} · {r.startedAt} · {r.id}</label>)}</>}
 <p>Single-file deterministic replay. Requires Python, Selenium and a configured sandbox-enabled Edge/Chrome Grid. No model or backend at runtime. Download does not run or verify a browser.</p>
 <code>python -I workflow_standalone.py --grid http://selenium:4444 --browser edge</code>
 <p>Only saved reviewed synthetic steps or complete current annotated recordings can export. Legacy/public journey evidence requires annotated recapture. Repair requires review and a new export.</p>
  {error&&<p role="alert" className="red">{error}</p>}{workflow&&<AirflowReplay workflow={workflow} runIds={runIds??chosen}/>}</section>;
}
