import { starterPython, checkCondition, evaluateCondition, type Condition, type PythonCode } from './python';
import { uid } from './workflow';
import type { Node, Edge } from '@xyflow/react';
export type Status = 'idle'|'queued'|'running'|'waiting'|'success'|'failed'|'skipped'|'cancelled'|'retrying';
export interface Config { target: string; region: string; metrics: string[]; timeRange: string; method: string; screenshot: boolean; prompt: string; retries: number; timeout: number; condition?:Condition; python?:PythonCode }
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
 ['condition','Branch / Condition','⑂','purple','SRE Bot Actions','Evaluate whether the error count is greater than zero.'],
 ['loop','Loop','↻','purple','SRE Bot Actions','Repeat a configured group of actions.'],
 ['summary','Summarize with LLM','✦','amber','SRE Bot Actions','Summarize observed evidence; no model connected in demo.'],
 ...['Lambda','CloudWatch','EventBridge','SNS','S3','DynamoDB','API Gateway','IAM','ECS','EKS','Step Functions','Systems Manager'].map(x=>[x.toLowerCase(),x,'λ','orange','AWS Services',`Inspect ${x} resources.`]),
 ...['ServiceNow','Jira','Slack','GitHub','Email','Kubernetes','Grafana','Dynatrace','OpenCode','OpenClaw','Custom Application'].map(x=>[x.toLowerCase(),x,x.slice(0,1),'cyan','Applications',`${x} integration configuration.`]),
 ...['Start','End','Merge','Variable','Set Variable','HTTP Request','Transform','Retry','Parallel','Subworkflow'].map(x=>[x.toLowerCase(),x,x==='Start'?'▶':x==='End'?'■':'◇','purple','Flow Control',`${x} control action.`])
].map(([id,title,icon,color,category,description])=>({id,title,icon,color,category,description}));
export type FlowNode = Node<{ action: string; label: string; config: Config }, 'action'>;
export interface Workflow { version: 1; name: string; nodes: FlowNode[]; edges: Edge[] }
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
 const w=v as Workflow;
 if(w.version!==1 || typeof w.name!=='string' || w.name.length>160 || !Array.isArray(w.nodes)||!Array.isArray(w.edges)||!w.nodes.length||w.nodes.length>300||w.edges.length>1000) throw Error('Invalid workflow schema or size');
 const ids=new Set<string>();
 for(const n of w.nodes){if(typeof n.id!=='string'||ids.has(n.id)||!actions.some(a=>a.id===n.data?.action)||typeof n.data.label!=='string'||n.data.label.length>160||!Number.isFinite(n.position?.x)||!Number.isFinite(n.position?.y))throw Error('Invalid or duplicate node');ids.add(n.id);const c=n.data.config;if(!c||typeof c.target!=='string'||c.target.length>2000||typeof c.region!=='string'||!Array.isArray(c.metrics)||c.metrics.some(m=>typeof m!=='string')||typeof c.prompt!=='string'||c.prompt.length>12000||!['API','Browser','Auto'].includes(c.method)||!Number.isFinite(c.retries)||c.retries<0||c.retries>10||!Number.isFinite(c.timeout)||c.timeout<1||c.timeout>3600)throw Error('Invalid node configuration');if(c.condition)checkCondition(c.condition);if(c.python&&(typeof c.python.source!=='string'||c.python.source.length>30000||!['starter','user','llm'].includes(c.python.origin)||!['pending','approved'].includes(c.python.review)))throw Error('Invalid Python source or provenance');}
 const edgeIds=new Set();for(const e of w.edges){if(!ids.has(e.source)||!ids.has(e.target)||e.source===e.target||edgeIds.has(e.id))throw Error('Invalid connection');edgeIds.add(e.id);}
 const done=new Set(),active=new Set();function visit(id:string){if(active.has(id))throw Error('Cycles are not supported in this template');if(done.has(id))return;active.add(id);w.edges.filter(e=>e.source===id).forEach(e=>visit(e.target));active.delete(id);done.add(id);}w.nodes.forEach(n=>visit(n.id));return structuredClone(w);
}
export function makeRun(workflow: Workflow, scenario: string): Run {
 const w=validateFlow(workflow);if(w.nodes.some(n=>n.data.config.python&&(n.data.config.python.origin!=='starter'||n.data.config.python.source!==starterPython(n))))throw Error('Custom/LLM Python is review/export only; demo execution cannot run it. Use a reviewed backend executor.');const start=w.nodes.filter(n=>n.data.action==='start');if(start.length!==1)throw Error('Demo run requires exactly one Start node');
 const events: Event[]=[];let ms=0;const visited=new Set<string>();let current:FlowNode|undefined=start[0];let failed=false;
 const emit=(n:FlowNode,status:Status,message:string,output?:Record<string,unknown>)=>events.push({id:`evt-${events.length}`,nodeId:n.id,ms:ms+=700,status,message,output});
 while(current){const n:FlowNode=current;visited.add(n.id);emit(n,'running',`Demo: ${n.data.label} started`);if(scenario==='waiting'&&n.data.action==='incident')emit(n,'waiting','Demo: waiting for manual approval');
 if(scenario==='retry'&&n.data.action==='logs'){emit(n,'retrying','Demo: transient timeout; retry scheduled');emit(n,'running','Demo: retry attempt 1');}
 if(scenario==='failure'&&n.data.action==='incident'){emit(n,'failed','Demo: ServiceNow permission denied (fixture)');failed=true;break;}
 const branch=n.data.config.condition?evaluateCondition(n.data.config.condition,n.data.config.condition.sample):scenario!=='healthy';
 const output=n.data.action==='condition'?{input:n.data.config.condition?.input??'errors',value:n.data.config.condition?.sample??(scenario==='healthy'?0:5),branch:branch?'yes':'no',demonstration:true}:n.data.action==='lambda'?{functionName:n.data.config.target,region:n.data.config.region,metrics:{errors:scenario==='healthy'?0:5,throttles:0,invocations:120},hasErrors:scenario!=='healthy'}:{target:n.data.config.target,demonstration:true};
 emit(n,'success',`Demo: ${n.data.label} completed`,output);
 const out=w.edges.filter(e=>e.source===n.id);if(out.length>1&&n.data.action!=='condition')throw Error('Demo runner supports serial actions and conditional branches only');
 const e=n.data.action==='condition'?out.find(e=>e.sourceHandle===(branch?'yes':'no')):out[0];current=e?w.nodes.find(n=>n.id===e.target):undefined;
 }
 for(const n of w.nodes)if(!visited.has(n.id))events.push({id:`evt-${events.length}`,nodeId:n.id,ms,status:'skipped',message:`Demo: ${n.data.label} not reached`});
 return {id:`demo-${Date.now()}`,started:new Date().toISOString(),scenario,workflow:w,events,status:failed?'Failed':'Success',duration:ms};
}
export function atTime(run:Run|undefined,ms:number){const states:Record<string,Status>={};const outputs:Record<string,Record<string,unknown>>={};let active='';for(const e of run?.events??[]){if(e.ms>ms)break;states[e.nodeId]=e.status;if(e.status!=='skipped')active=e.nodeId;if(e.output)outputs[e.nodeId]=e.output;}return {states,outputs,active};}

export function linkNodes(workflow:Workflow, source:string, target:string, sourceHandle:string|null=null):Workflow {
 const from=workflow.nodes.find(n=>n.id===source),to=workflow.nodes.find(n=>n.id===target);
 if(!from||!to)throw Error('Choose two existing nodes');
 if(from.data.action==='end'||to.data.action==='start')throw Error('End has no output; Start has no input');
 if(source===target)throw Error('A node cannot connect to itself');
 const handle=from.data.action==='condition'?(sourceHandle||'yes'):null;
 if(from.data.action==='condition'&&!['yes','no'].includes(handle!))throw Error('Choose the Yes or No branch');
 if(workflow.edges.some(e=>e.source===source&&e.target===target&&(e.sourceHandle||null)===handle))throw Error('These nodes are already linked');
 return validateFlow({...workflow,edges:[...workflow.edges,{id:uid('edge'),source,target,sourceHandle:handle,targetHandle:null,label:handle?.toUpperCase(),style:{stroke:handle==='no'?'#FF4D71':'#00D68F',strokeWidth:2}}]});
}
