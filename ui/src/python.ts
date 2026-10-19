import type { FlowNode } from './sre';
export type Operator='>'|'>='|'<'|'<='|'=='|'!=';
export interface Condition { input:string; operator:Operator; threshold:number; sample:number }
export interface PythonCode { source:string; origin:'starter'|'user'|'llm'; review:'pending'|'approved'; model?:string }
export const defaultCondition:Condition={input:'i',operator:'>',threshold:3,sample:5};
export function checkCondition(c:Condition){if(!/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(c.input)||['True','False','None','class','def','if','else','for','import','return','lambda','in','is','not','and','or','while','try','with','async','await','yield','del','from','global','nonlocal','pass','raise','assert','break','continue','except','finally','as','elif'].includes(c.input)||!['>','>=','<','<=','==','!='].includes(c.operator)||!Number.isFinite(c.threshold)||!Number.isFinite(c.sample))throw Error('Condition requires a Python input name, supported comparison and finite numeric values');}
export function evaluateCondition(c:Condition,value:number){checkCondition(c);switch(c.operator){case '>':return value>c.threshold;case '>=':return value>=c.threshold;case '<':return value<c.threshold;case '<=':return value<=c.threshold;case '==':return value===c.threshold;case '!=':return value!==c.threshold;}}
export function starterPython(n:FlowNode):string {
 const c=n.data.config;
 if(n.data.action==='condition'){
  if(c.condition){checkCondition(c.condition);const p=c.condition;return `# Editable Python starter. No LLM has been called.\ndef run(inputs, context=None):\n    ${p.input} = inputs[${JSON.stringify(p.input)}]\n    if isinstance(${p.input}, bool) or not isinstance(${p.input}, (int, float)):\n        raise ValueError("Expected a numeric input")\n    return {"branch": "yes" if ${p.input} ${p.operator} ${p.threshold} else "no"}\n`;}
  return '# Editable Python starter: Lambda investigation branch.\ndef run(inputs, context=None):\n    errors = inputs["errors"]\n    return {"branch": "yes" if errors > 0 else "no"}\n';
 }
 if(n.data.action==='start'||n.data.action==='end')return '# Editable Python starter.\ndef run(inputs, context=None):\n    return {"status": "'+(n.data.action==='start'?'started':'completed')+'"}\n';
 const payload=JSON.stringify({action:n.data.action,target:c.target,region:c.region,metrics:c.metrics,timeRange:c.timeRange,method:c.method});
 return `# Editable Python starter. Integrations and webpage discovery are pending.\nimport json\n\ndef run(inputs, context=None):\n    config = json.loads(${JSON.stringify(payload)})\n    return {"status": "pending", "action": config["action"],\n            "config": config, "reason": "Execution adapter not connected"}\n`;
}
export function pythonRequest(n:FlowNode,instructions:string){return {version:1,nodeId:n.id,action:n.data.action,config:{target:n.data.config.target,region:n.data.config.region,condition:n.data.config.condition},instructions,contract:'def run(inputs, context=None) -> dict',constraints:['Return Python source only','Never execute generated code','Use inputs for parameters','Webpage perception/selection is pending; do not fabricate selectors','Mutating integrations must remain pending until explicitly authorized']};}
export function exportPython(nodes:FlowNode[]){return '# SRE Flow Builder — review-only Python export. Do not import or execute unreviewed code.\n# Integrations/webpage perception are pending. The frontend never runs custom Python.\n\n'+nodes.map((n,i)=>`# Node ${JSON.stringify(n.id)}: ${n.data.label.replace(/[\r\n]/g,' ')}\n${(n.data.config.python?.source??starterPython(n)).replace(/^def run\(/m,`def node_${i}(`)}\n`).join('\n');}
