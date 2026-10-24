import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { expect, it } from 'vitest';
import { buildDAG, exportDAGPython } from './dag';
import { template, linkNodes } from './sre';
import { loopTemplate } from './control';
import { createSeed } from './workflow';
import { importPageSeed } from './page-seed';
it('loads actual frontend Python DAGs through the safe Python dataclass loader and graphlib planner',()=>{
 const parallel=template();parallel.nodes[1].data.action='parallel';const fork=linkNodes(parallel,parallel.nodes[1].id,'summary');const workflows=[fork,template(),loopTemplate(),importPageSeed(createSeed('https://example.com/{service}?query={xyz}'))];const payload=workflows.map(w=>({python:exportDAGPython(w),spec:buildDAG(w),workflow:w}));
 const code='import json,sys; from triage.dag import load_python,DAG,from_workflow; rows=json.load(sys.stdin); results=[]\nfor row in rows:\n d=load_python(row["python"]); assert [(t.routes,t.depends_on) for t in from_workflow(row["workflow"]).tasks]==[(t.routes,t.depends_on) for t in d.tasks]; assert d.to_spec()==row["spec"], "cross-language schema drift"; assert load_python(d.to_python()).to_spec()==d.to_spec(); results.append(d.plan())\nprint(json.dumps(results))';
 const result=spawnSync('python3',['-c',code],{cwd:fileURLToPath(new URL('../..',import.meta.url)),input:JSON.stringify(payload),encoding:'utf8'});expect(result.status,result.stderr).toBe(0);const plans=JSON.parse(result.stdout);expect(plans[0].root[0]).toBe('start');expect(Object.keys(plans[2].bodies)).toHaveLength(1);expect(plans[1].execution).toBe('not started');
});
