import { useStudio } from './store';
import type { BrowserPolicy } from './sre';
const fixture:BrowserPolicy={allowed_actions:['show-errors','open-details','return-home'],expected:{id:'errors',text:'Errors: 0'},max_steps:3};
export default function BrowserPolicyEditor({nodeId}:{nodeId:string}){
 const s=useStudio(),node=s.workflow.nodes.find(n=>n.id===nodeId);
 if(!node||['start','end','condition','loop','loop-end','parallel'].includes(node.data.action))return <p>Select an application task to configure its Grid test.</p>;
 const config=node.data.config,policy=config.browser;
 const update=(patch:Partial<typeof config>)=>{const latest=useStudio.getState();if(latest.mode==='Replay')return;latest.change({...latest.workflow,nodes:latest.workflow.nodes.map(n=>n.id===nodeId?{...n,data:{...n.data,config:{...n.data.config,...patch}}}:n)});};
 const readonly=policy&&'mode' in policy;
 return <fieldset disabled={s.mode==='Replay'}><legend>Saved task · Edge browser policy</legend>
 <label>Browser test mode<select aria-label="Browser test mode" value={!policy?'none':readonly?'or9':'annotated'} onChange={e=>{if(e.target.value==='none')update({browser:undefined});else if(e.target.value==='or9')update({browser:{mode:'read-only-or9'},target:'https://or9.ca/',prompt:'Verify the public or9.ca homepage loads with a title and visible body. No actions or capture.',method:'Browser'});else update({browser:structuredClone(fixture),target:'http://127.0.0.1:8080/',prompt:'Inspect the errors chart and verify Errors: 0 using approved read-only controls.',method:'Browser'});}}><option value="none">Not a browser test</option><option value="or9">or9.ca · read-only homepage</option><option value="annotated">Annotated synthetic page · actions and recording</option></select></label>
 {policy&&<><label>Approved target<input aria-label="Browser target" disabled={!!readonly} value={config.target} onChange={e=>update({target:e.target.value})}/></label><label>Browser task goal<textarea aria-label="Browser task goal" value={config.prompt} onChange={e=>update({prompt:e.target.value})}/></label>
 {!('mode' in policy)&&<><label>Allowed action IDs<input aria-label="Allowed browser actions" value={policy.allowed_actions.join(',')} onChange={e=>update({browser:{...policy,allowed_actions:e.target.value.split(',').map(v=>v.trim())}})}/></label><label>Expected result ID<input aria-label="Expected browser result ID" value={policy.expected.id} onChange={e=>update({browser:{...policy,expected:{...policy.expected,id:e.target.value}}})}/></label><label>Expected visible text<input aria-label="Expected browser result text" value={policy.expected.text} onChange={e=>update({browser:{...policy,expected:{...policy.expected,text:e.target.value}}})}/></label><label>Maximum browser steps<input aria-label="Maximum browser steps" type="number" min="1" max="5" value={policy.max_steps} onChange={e=>update({browser:{...policy,max_steps:Number(e.target.value)}})}/></label></>}
 <p>Save the DAG, then reload its saved policy. The backend URL allowlist and network policy still apply; editing this form does not expand permissions.</p></>}
 </fieldset>;
}
