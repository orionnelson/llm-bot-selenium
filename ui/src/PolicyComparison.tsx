import {useEffect,useState} from 'react';
import BrowserPolicyEditor from './BrowserPolicyEditor';
import {loadDAG} from './backend';
import type {TaskSpec} from './dag';

export default function PolicyComparison({nodeId}:{nodeId:string}){
 const [saved,setSaved]=useState<{revision:string;task?:TaskSpec}>(),[error,setError]=useState('');
 useEffect(()=>{let alive=true;setSaved(undefined);setError('');loadDAG().then(d=>{if(alive)setSaved({revision:d.revision,task:d.definition.tasks.find(t=>t.task_id===nodeId)});}).catch(e=>{if(alive)setError(String(e));});return()=>{alive=false;};},[nodeId]);
 return <div className="policy-comparison"><section aria-label="Current draft browser policy"><BrowserPolicyEditor nodeId={nodeId}/></section>
 <section className="saved-policy" aria-label="Saved canonical browser policy"><h4>Saved canonical policy</h4><p>This snapshot is read-only. Editing the current draft does not change it until Save succeeds.</p>{error?<p role="alert">{error}</p>:!saved?<p role="status">Loading the saved DAG…</p>:saved.task?<><p><b>{saved.task.label}</b> · {saved.task.task_id}</p><dl><dt>Saved target</dt><dd>{String(saved.task.params.target??'Not configured')}</dd><dt>Saved mode</dt><dd>{String((saved.task.params.browser as {mode?:string}|undefined)?.mode??(saved.task.params.browser?'Annotated synthetic test':'Not a browser test'))}</dd></dl><small>Revision: {saved.revision.slice(0,12)}</small></>:<p>This draft node has no matching task in the saved canonical DAG.</p>}</section></div>;
}
