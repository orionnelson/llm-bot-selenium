import { spawn } from 'node:child_process';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { once } from 'node:events';
import { afterAll, beforeAll, expect, it, vi } from 'vitest';
import { loadDAG, commitDAG, projectDAG, draftKey } from './backend';
import { buildDAG } from './dag';

let child, directory;
beforeAll(async()=>{
 directory=await mkdtemp(join(tmpdir(),'dag-backend-'));
 // Deliberately authored in Python, not generated from an editor/template.
 await writeFile(join(directory,'dag.py'),`from triage.dag import DAG, Task
 dag = DAG(name='Python owns this graph', tasks=(
 Task(task_id='python-start', label='Backend start', action='start', kind='start', routes={'next': 'python-end'}),
 Task(task_id='python-end', label='Backend end', action='end', kind='end', depends_on=('python-start',)),
 ))
`.replace('\n dag =','\ndag =').replace('\n ))','\n))'));
 child=spawn('python3',['-u','-c',`from http.server import HTTPServer
from pathlib import Path
import sys
from triage.dag_server import handler
from triage import test_codegen
model_ready=False
def model_api(path,payload=None):
 global model_ready
 if path=='/v1/models':return {'data':[{'id':test_codegen.MODEL,'status':{'value':'loaded' if model_ready else 'unloaded'}}]}
 if path=='/models/load':
  model_ready=True
  return {'status':'ok'}
 if path=='/models/unload':
  model_ready=False
  return {'status':'ok'}
 return {'model':test_codegen.MODEL,'choices':[{'finish_reason':'stop','message':{'content':'def run(inputs, context=None):\\n    return {\"status\": \"pending\"}\\n'}}]}
test_codegen.smol=model_api
root=Path(sys.argv[1])
with HTTPServer(('127.0.0.1',0),handler(root/'dag.py',root,test_mode=True)) as server:
 print(server.server_port,flush=True)
 server.serve_forever()
`,directory],{cwd:fileURLToPath(new URL('../..',import.meta.url)),stdio:'pipe'});
 const port=await new Promise((resolve,reject)=>{
  let output='',error='';child.stderr.on('data',data=>error+=data);
  child.once('error',reject);child.once('exit',()=>reject(Error(error||'Backend exited')));
  child.stdout.on('data',data=>{output+=data;if(output.includes('\n'))resolve(output.trim());});
 });
 const nativeFetch=globalThis.fetch;
 vi.stubGlobal('fetch',(input,init)=>nativeFetch(new URL(input,`http://127.0.0.1:${port}`),init));
},15000);
afterAll(async()=>{vi.unstubAllGlobals();if(child&&child.exitCode===null){const exited=once(child,'exit');child.kill();await exited;}if(directory)await rm(directory,{recursive:true,force:true});});

it('renders a Python-authored backend DAG, independent of the canvas template',async()=>{
 const value=await loadDAG();
 const view=projectDAG(value,{version:'sre-layout/v1',positions:{'python-start':{x:77,y:33}}});
 expect(view.name).toBe('Python owns this graph');
 expect(view.nodes.map(n=>n.id)).toEqual(['python-start','python-end']);
 expect(view.nodes[0].position).toEqual({x:77,y:33});
 expect(value.plan.root).toEqual(['python-start','python-end']);
 expect(value.plan.execution).toBe('not started');
 expect(buildDAG(view)).toEqual(buildDAG(projectDAG(value)));
});
it('commits an edit through the real backend and renders its returned canonical DAG',async()=>{
 const value=await loadDAG();const view=projectDAG(value);view.name='Backend validated edit';
 const saved=await commitDAG(view,value.revision);
 expect(projectDAG(saved).name).toBe('Backend validated edit');
 expect(await readFile(join(directory,'dag.py'),'utf8')).toBe(saved.python);
 expect(saved.revision).not.toBe(value.revision);
 expect(saved.definition).not.toHaveProperty('positions');
 await expect(commitDAG(view,value.revision)).rejects.toThrow('Backend DAG changed');
 expect((await loadDAG()).revision).toBe(saved.revision);
});
it('does not silently accept a server rejection or HTML from a static-only host',async()=>{
 const fetch=globalThis.fetch;
 vi.stubGlobal('fetch',async()=>new Response('<html>old static host</html>',{status:404}));
 try{await expect(loadDAG()).rejects.toThrow('DAG backend unavailable');}finally{vi.stubGlobal('fetch',fetch);}
});

it('ignores React Flow measurements but detects author edits while requests are pending',async()=>{
 const view=projectDAG(await loadDAG()),key=draftKey(view);
 const measured={...view,nodes:view.nodes.map(n=>({...n,measured:{width:190,height:80},selected:true}))};
 expect(draftKey(measured)).toBe(key);
 measured.nodes[0].data={...measured.nodes[0].data,label:'Unsaved edit'};
 expect(draftKey(measured)).not.toBe(key);
 expect(draftKey({...view,nodes:view.nodes.map(n=>({...n,position:{x:42,y:19}}))})).not.toBe(key);
});

it('refuses an ambiguous Python definition rather than projecting its last keyword',async()=>{
 const path=join(directory,'dag.py'),source=await readFile(path,'utf8');
 await writeFile(path,source.replace('DAG(name=', "DAG(name='Hidden', name="));
 try{
  await expect(loadDAG()).rejects.toThrow('DAG backend unavailable or rejected the definition (422)');
  expect(await readFile(path,'utf8')).toContain("DAG(name='Hidden', name=");
 }finally{await writeFile(path,source);}
});

it('real HTTP generation returns an inert test candidate, never changing the saved DAG',async()=>{
 const saved=await loadDAG(),before=await readFile(join(directory,'dag.py'),'utf8');
 const response=await fetch('/api/python/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nodeId:saved.definition.tasks[0].task_id,instructions:'Synthetic test only'})});
 expect(response.status).toBe(200);const candidate=await response.json();
 expect(candidate.model).toBe('Qwen3.6-35B-A3B-UD-Q4_K_M-no-think');
 expect(candidate.review).toBe('pending');expect(candidate.executed).toBe(false);
 expect(await readFile(join(directory,'dag.py'),'utf8')).toBe(before);
});
