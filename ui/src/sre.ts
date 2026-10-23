import { validateSnippet, type Snippet } from './snippets';
import { loopConfig, validateLoop, loopContinues, type LoopConfig } from './control';
import { starterPython, checkCondition, evaluateCondition, type Condition, type PythonCode } from './python';
import { uid } from './workflow';
import type { Node, Edge } from '@xyflow/react';
export type Status = 'idle'|'queued'|'running'|'waiting'|'success'|'failed'|'skipped'|'cancelled'|'retrying';
export interface Config { target: string; region: string; metrics: string[]; timeRange: string; method: string; screenshot: boolean; prompt: string; retries: number; timeout: number; condition?:Condition; python?:PythonCode; loop?:LoopConfig; loopOwner?:string; snippet?:Snippet }
export interface Action { id: string; title: string; icon: string; color: string; category: string; description: string }
export const actions: Action[] = [
 ['lambda','Check Lambda Page','λ','orange','SRE Bot Actions','Inspect a Lambda function and extract operational metrics.'],
 ['application','Check Application','◎','cyan','SRE Bot Actions','Inspect application health and availability.'],
 ['logs','Query Logs','⌕','purple','SRE Bot Actions','Pull relevant operational logs for the affected resource.'],
 ['incident','Create Incident','C','pink','SRE Bot Actions','Prepare an incident with an evidence summary.'],
 ['update','Update Incident','▣','cyan','SRE Bot Actions','Update an existing incident with findings.'],
 ['notify','Send Notification','#','pink','SRE Bot Actions','Notify the configured channel with incident details.'],
 ['command','Run Command','>_','green','SRE Bot Actions','Execute an explicitly approved command.'],
 ['delay','Wait / Delay','◷','purple','SRE Bot Actions','Wait for an interval or event.'],
 ['condition','Branch / Condition','⑂','purple','SRE Bot Actions','Evaluate the configured predicate and take exactly one IF / ELSE branch.'],
 ['loop','For / While Loop','↻','purple','SRE Bot Actions','Repeat a configured group of actions.'],
 ['loop-end','Continue / Loop End','↵','purple','Internal Control','Return to the paired bounded loop.'],
 ['snippet','Browser Snippet','▤','cyan','SRE Bot Actions','Reusable URL and ordered triage action segment; browser execution pending.'],
 ['summary','Summarize with LLM','✦','amber','SRE Bot Actions','Summarize observed evidence; no model connected in demo.'],
 ...['Lambda','CloudWatch','EventBridge','SNS','S3','DynamoDB','API Gateway','IAM','ECS','EKS','Step Functions','Systems Manager'].map(x=>[x.toLowerCase(),x,'λ','orange','AWS Services',`Inspect ${x} resources.`]),
 ...['ServiceNow','Jira','Slack','GitHub','Email','Kubernetes','Grafana','Dynatrace','OpenCode','OpenClaw','Custom Application'].map(x=>[x.toLowerCase(),x,x.slice(0,1),'cyan','Applications',`${x} integration configuration.`]),
 ...['Start','End','Merge','Variable','Set Variable','HTTP Request','Transform','Retry','Parallel','Subworkflow'].map(x=>[x.toLowerCase(),x,x==='Start'?'▶':x==='End'?'■':'◇','purple','Flow Control',`${x} control action.`])
].map(([id,title,icon,color,category,description])=>({id,title,icon,color,category,description}));
export type FlowNode = Node<{ action: string; label: string; config: Config }, 'action'>;
export interface Workflow { version: 1; name: string; nodes: FlowNode[]; edges: Edge[]; snippets?:Snippet[] }
export interface Event { id: string; nodeId: string; ms: number; status: Status; message: string; output?: Record<string,unknown> }
export interface Run { id: string; started: string; scenario: string; workflow: Workflow; events: Event[]; status: string; duration: number }
export const config = (target='user-function'): Config => ({target,region:'ca-central-1',metrics:['Errors','Throttles','Duration'],timeRange:'1h',method:'Auto',screenshot:true,prompt:'Inspect {{ target }}. Summarize only observed operational evidence and identify uncertainty.',retries:2,timeout:30});
export function template(): Workflow {
 const data: [string,string,number,number,string?][]=[['start','start',20,190],['check-lambda','lambda',185,155],['check-errors','condition',430,190],['query-logs','logs',670,110],['create-incident','incident',915,110,'ServiceNow / application'],['notify','notify',1160,110,'#sre-alerts'],['summary','summary',670,430,'Lambda metrics'],['end','end',1410,240]];
 const pairs=[['start','check-lambda'],['check-lambda','check-errors'],['check-errors','query-logs','yes'],['check-errors','summary','no'],['query-logs','create-incident'],['create-incident','notify'],['notify','end'],['summary','end']];
 return {version:1,name:'Incident Response Automation',nodes:data.map(([id,action,x,y,target])=>({id,type:'action',position:{x,y},data:{action,label:action==='condition'?'Any errors found?':actions.find(a=>a.id===action)!.title,config:config(target)}})),edges:pairs.map(([source,target,branch],i)=>({id:`e${i}`,source,target,sourceHandle:branch,label:branch?.toUpperCase(),style:{stroke:branch==='yes'?'#00D68F':branch==='no'?'#FF4D71':'#9BAEC5',strokeWidth:2}}))};
}
export function validateFlow(v: unknown): Workflow {
 if (!v || typeof v!=='object') throw Error('Expected workflow object');
 const w=structuredClone(v) as Workflow;
 if(w.version!==1 || typeof w.name!=='string' || w.name.length>160 || !Array.isArray(w.nodes)||!Array.isArray(w.edges)||!w.nodes.length||w.nodes.length>300||w.edges.length>1000) throw Error('Invalid workflow schema or size');
 // Upgrade previously saved placeholder loops without dropping their serial continuation.
 for(const n of [...w.nodes])if(n.data?.action==='loop'&&n.data.config&&!n.data.config.loop){const end=uid('loop_end'),body=uid('body');n.data.config.loop=loopConfig(end);w.edges=w.edges.map(e=>e.source===n.id?{...e,sourceHandle:'done',label:'DONE'}:e);w.nodes.push({id:body,type:'action',position:{x:n.position.x+250,y:n.position.y},data:{action:'application',label:'Migrated loop body — configure action',config:config()}},{id:end,type:'action',position:{x:n.position.x+500,y:n.position.y},data:{action:'loop-end',label:'Continue / next iteration',config:{...config(),loopOwner:n.id}}});w.edges.push({id:uid('edge'),source:n.id,target:body,sourceHandle:'body',label:'BODY'},{id:uid('edge'),source:body,target:end},{id:uid('edge'),source:end,target:n.id,sourceHandle:'continue',targetHandle:'repeat',label:'REPEAT'});}
 if(w.nodes.length>300||w.edges.length>1000)throw Error('Migrated graph exceeds node/edge limits');
 const ids=new Set<string>();
 for(const n of w.nodes){if(typeof n.id!=='string'||ids.has(n.id)||!actions.some(a=>a.id===n.data?.action)||typeof n.data.label!=='string'||n.data.label.length>160||!Number.isFinite(n.position?.x)||!Number.isFinite(n.position?.y))throw Error('Invalid or duplicate node');ids.add(n.id);const c=n.data.config;if(!c||typeof c.target!=='string'||c.target.length>2000||typeof c.region!=='string'||!Array.isArray(c.metrics)||c.metrics.some(m=>typeof m!=='string')||typeof c.prompt!=='string'||c.prompt.length>12000||!['API','Browser','Auto'].includes(c.method)||!Number.isFinite(c.retries)||c.retries<0||c.retries>10||!Number.isFinite(c.timeout)||c.timeout<1||c.timeout>3600)throw Error('Invalid node configuration');if(c.snippet)validateSnippet(c.snippet);if(c.condition)checkCondition(c.condition);if(c.python&&(typeof c.python.source!=='string'||c.python.source.length>30000||!['starter','user','llm'].includes(c.python.origin)||!['pending','approved'].includes(c.python.review)))throw Error('Invalid Python source or provenance');}
 for(const n of w.nodes){if(n.data.action==='loop'){validateLoop(n.data.config.loop!);const end=w.nodes.find(x=>x.id===n.data.config.loop!.endNodeId);if(end?.data.action!=='loop-end'||end.data.config.loopOwner!==n.id)throw Error('Loop must have its paired Continue boundary');}if(n.data.action==='loop-end'&&!w.nodes.some(x=>x.id===n.data.config.loopOwner&&x.data.config.loop?.endNodeId===n.id))throw Error('Orphan loop boundary');}
 const isReturn=(e:Edge)=>{const n=w.nodes.find(n=>n.id===e.source);return n?.data.action==='loop-end'&&n.data.config.loopOwner===e.target&&e.sourceHandle==='continue'&&e.targetHandle==='repeat';};
 if(w.snippets&&(!Array.isArray(w.snippets)||w.snippets.length>100))throw Error('Snippet library must contain at most 100 entries');w.snippets?.forEach(validateSnippet);
 const edgeIds=new Set();for(const e of w.edges){if(!ids.has(e.source)||!ids.has(e.target)||e.source===e.target||edgeIds.has(e.id))throw Error('Invalid connection');edgeIds.add(e.id);const from=w.nodes.find(n=>n.id===e.source)!;if(from.data.action==='loop'&&!['body','done'].includes(e.sourceHandle||''))throw Error('Loop output must be BODY or DONE');if((from.data.action==='loop-end'||e.targetHandle==='repeat')&&!isReturn(e))throw Error('Continue can only return to its paired loop Repeat input');}
 const done=new Set(),active=new Set();function visit(id:string){if(active.has(id))throw Error('Cycles are not supported in this template');if(done.has(id))return;active.add(id);w.edges.filter(e=>e.source===id&&!isReturn(e)).forEach(e=>visit(e.target));active.delete(id);done.add(id);}w.nodes.forEach(n=>visit(n.id));const clean=w;if(clean.snippets)clean.snippets=clean.snippets.map(validateSnippet);for(const n of clean.nodes)if(n.data.config.snippet)n.data.config.snippet=validateSnippet(n.data.config.snippet);return clean;
}
export function makeRun(workflow:Workflow,scenario:string):Run {
 const w=validateFlow(workflow);validateOutputs(w);if(w.nodes.some(n=>n.data.config.python&&(n.data.config.python.origin!=='starter'||n.data.config.python.source!==starterPython(n))))throw Error('Custom/LLM Python is review/export only; demo execution cannot run it. Use a reviewed backend executor.');
 const starts=w.nodes.filter(n=>n.data.action==='start');if(starts.length!==1)throw Error('Demo run requires exactly one Start node');
 const events:Event[]=[];const visited=new Set<string>();let ms=0,status='Success',active=starts[0];
 const emit=(n:FlowNode,state:Status,message:string,output?:Record<string,unknown>)=>{active=n;if(events.length>=2500)throw Error('Demo event budget exceeded');visited.add(n.id);events.push({id:`evt-${events.length}`,nodeId:n.id,ms:ms+=700,status:state,message,output});};
 function edge(n:FlowNode,handle?:string){const out=w.edges.filter(e=>e.source===n.id&&(handle===undefined||e.sourceHandle===handle));if(out.length>1)throw Error('Each control port or serial output must have one destination');return out[0]?.target;}
 function walk(id:string|undefined,stopAt?:string,env:Record<string,number>={},depth=0):boolean {
  if(depth>4)throw Error('Demo supports at most four nested loop blocks');
  while(id){const n=w.nodes.find(x=>x.id===id)!;active=n;
   if(n.id===stopAt){emit(n,'success','Demo: continue / next iteration');return true;}
   if(n.data.action==='loop-end')throw Error('Continue boundary reached outside its loop body');
   emit(n,'running',`Demo: ${n.data.label} started`);
   if(n.data.action==='parallel'){emit(n,'waiting','Parallel plan ready; concurrent execution adapter pending');status='Pending';return false;}
   if(n.data.action==='snippet'){emit(n,'waiting','Snippet plan ready; live/recorded browser execution adapter pending');status='Pending';return false;}
   if(n.data.action==='loop'){
    const c=n.data.config.loop!;validateLoop(c);let value=c.start,count=0;
    const body=edge(n,'body');if(!body)throw Error('Connect the loop BODY port');
    const boundary=w.nodes.find(x=>x.id===c.endNodeId)!;
    if(!w.edges.some(e=>e.source===boundary.id&&e.target===n.id&&e.sourceHandle==='continue'&&e.targetHandle==='repeat'))throw Error('Connect Continue back to the paired Repeat input');
    while(loopContinues(c,value)){
     active=n;if(count>=c.maxIterations)throw Error(`Loop iteration cap ${c.maxIterations} reached before exit`);
     count++;emit(n,'running',`Demo: iteration ${count} · ${c.variable} = ${value}`,{iteration:count,variable:c.variable,value});
     if(!walk(body,c.endNodeId,{...env,[c.variable]:value},depth+1))return false;
     value+=c.step;
    }
    emit(n,'success',`Demo: loop completed after ${count} iterations`,{iterations:count,nextValue:value,mode:c.mode});id=edge(n,'done');continue;
   }
   if(scenario==='waiting'&&n.data.action==='incident')emit(n,'waiting','Demo: waiting for manual approval');
   if(scenario==='retry'&&n.data.action==='logs'){emit(n,'retrying','Demo: transient timeout; retry scheduled');emit(n,'running','Demo: retry attempt 1');}
   if(scenario==='failure'&&n.data.action==='incident'){emit(n,'failed','Demo: ServiceNow permission denied (fixture)');status='Failed';return false;}
   const c=n.data.config.condition;const value=c?(Object.hasOwn(env,c.input)?env[c.input]:c.sample):(scenario==='healthy'?0:5);const branch=c?evaluateCondition(c,value):scenario!=='healthy';
   const output=n.data.action==='condition'?{input:c?.input??'errors',value,branch:branch?'yes':'no',demonstration:true}:n.data.action==='lambda'?{functionName:n.data.config.target,region:n.data.config.region,metrics:{errors:scenario==='healthy'?0:5,throttles:0,invocations:120},hasErrors:scenario!=='healthy'}:{target:n.data.config.target,demonstration:true};
   emit(n,'success',`Demo: ${n.data.label} completed`,output);id=edge(n,n.data.action==='condition'?(branch?'yes':'no'):undefined);
  }
  if(stopAt)throw Error('Loop body must reach its paired Continue boundary');return true;
 }
 try{walk(starts[0].id);}catch(error){status='Failed';events.push({id:`evt-${events.length}`,nodeId:active.id,ms:ms+=700,status:'failed',message:String(error)});}
 for(const n of w.nodes)if(!visited.has(n.id))events.push({id:`evt-${events.length}`,nodeId:n.id,ms,status:'skipped',message:`Demo: ${n.data.label} not reached`});
 return {id:`demo-${Date.now()}`,started:new Date().toISOString(),scenario,workflow:w,events,status,duration:ms};
}
export function atTime(run:Run|undefined,ms:number){const states:Record<string,Status>=Object.create(null);const outputs:Record<string,Record<string,unknown>>=Object.create(null);let active='';for(const e of run?.events??[]){if(e.ms>ms)break;states[e.nodeId]=e.status;if(e.status!=='skipped')active=e.nodeId;if(e.output)outputs[e.nodeId]=e.output;}return {states,outputs,active};}

// Draft rewiring may temporarily fan out; saving/exporting/running must not choose a destination silently.
export function validateOutputs(w:Workflow):void {
 const outputs=new Set<string>();
 for(const e of w.edges){const parallel=w.nodes.find(n=>n.id===e.source)?.data.action==='parallel';const key=JSON.stringify([e.source,parallel?e.target:e.sourceHandle||'next']);if(outputs.has(key)){const node=w.nodes.find(n=>n.id===e.source);throw Error(`Output ${e.sourceHandle||'next'} on "${node?.data.label??e.source}" has multiple connections. Delete the unwanted connection before saving.`);}outputs.add(key);}
}

export function linkNodes(workflow:Workflow, source:string, target:string, sourceHandle:string|null=null,targetHandle:string|null=null):Workflow {
 const from=workflow.nodes.find(n=>n.id===source),to=workflow.nodes.find(n=>n.id===target);
 if(!from||!to)throw Error('Choose two existing nodes');
 if(from.data.action==='end'||to.data.action==='start')throw Error('End has no output; Start has no input');
 if(source===target)throw Error('A node cannot connect to itself');
 if(targetHandle==='repeat'&&(from.data.action!=='loop-end'||from.data.config.loopOwner!==target))throw Error('Repeat input accepts only its paired Continue boundary');
 const handle=from.data.action==='condition'?(sourceHandle||'yes'):from.data.action==='loop'?(sourceHandle||'body'):from.data.action==='loop-end'?'continue':null;
 if(from.data.action==='loop'&&!['body','done'].includes(handle!))throw Error('Choose BODY or DONE');
 if(from.data.action==='loop-end'&&from.data.config.loopOwner!==target)throw Error('Continue must return to its paired loop');
 if(from.data.action==='condition'&&!['yes','no'].includes(handle!))throw Error('Choose the Yes or No branch');
 if(workflow.edges.some(e=>e.source===source&&e.target===target&&(e.sourceHandle||null)===handle))throw Error('These nodes are already linked');
 const candidate=validateFlow({...workflow,edges:[...workflow.edges,{id:uid('edge'),source,target,sourceHandle:handle,targetHandle:from.data.action==='loop-end'?'repeat':null,label:handle?.toUpperCase(),style:{stroke:handle==='no'?'#FF4D71':['body','continue'].includes(handle||'')?'#A36BFF':'#00D68F',strokeWidth:2,...(handle==='continue'?{strokeDasharray:'6 4'}:{})}}]});
 return candidate;
}

export function removeNodes(w:Workflow,ids:string[]):Workflow {const removed=new Set(ids);for(const n of w.nodes)if(removed.has(n.id)){if(n.data.action==='loop')removed.add(n.data.config.loop!.endNodeId);if(n.data.action==='loop-end')removed.add(n.data.config.loopOwner!);}return validateFlow({...w,nodes:w.nodes.filter(n=>!removed.has(n.id)),edges:w.edges.filter(e=>!removed.has(e.source)&&!removed.has(e.target))});}
