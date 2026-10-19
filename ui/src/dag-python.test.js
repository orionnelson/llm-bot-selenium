import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { expect, it } from 'vitest';
import { buildDAG, exportDAGPython } from './dag';
import { template } from './sre';
import { loopTemplate } from './control';
it('loads actual frontend Python DAGs through the safe Python dataclass loader and graphlib planner',()=>{
 const workflows=[template(),loopTemplate()];const payload=workflows.map(w=>({python:exportDAGPython(w),spec:buildDAG(w)}));
 const code='import json,sys; from triage.dag import load_python,DAG; rows=json.load(sys.stdin); results=[]\nfor row in rows:\n d=load_python(row["python"]); assert d.to_spec()==row["spec"], "cross-language schema drift"; assert load_python(d.to_python()).to_spec()==d.to_spec(); results.append(d.plan())\nprint(json.dumps(results))';
 const result=spawnSync('python3',['-c',code],{cwd:fileURLToPath(new URL('../..',import.meta.url)),input:JSON.stringify(payload),encoding:'utf8'});expect(result.status,result.stderr).toBe(0);const plans=JSON.parse(result.stdout);expect(plans[0].root[0]).toBe('start');expect(Object.keys(plans[1].bodies)).toHaveLength(1);expect(plans[1].execution).toBe('not started');
});
