import { afterEach, expect, it, vi } from 'vitest';
import { renderToString } from 'react-dom/server';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import DAGInspector from './DAGInspector';
import { exportStandalone } from './browser';
import { buildDAG } from './dag';
import { template } from './sre';

afterEach(()=>vi.unstubAllGlobals());
it('shows standalone download, dependency/invocation hints and accurately labels inert definition',()=>{
 const html=renderToString(<DAGInspector workflow={template()}/>);
 expect(html).toContain('Export standalone Selenium .py');
 expect(html).toContain('Export inert Python DAG definition');
 expect(html).toContain('python -I workflow_standalone.py');
 expect(html).toContain('Download does not run or verify a browser');
});
it('sends only selected run IDs and expected revision and exposes export rejection',async()=>{
 const fetcher=vi.fn().mockResolvedValueOnce(new Response('# standalone', {status:200}))
  .mockResolvedValueOnce(new Response(JSON.stringify({error:'Missing wait evidence; recapture'}),{status:422,headers:{'Content-Type':'application/json'}}));
 vi.stubGlobal('fetch',fetcher);
 expect(await exportStandalone('revision',['a'.repeat(32)])).toBe('# standalone');
 const [path,init]=fetcher.mock.calls[0];expect(path).toBe('/api/dag/export/selenium');
 expect(init.headers['If-Match']).toBe('revision');expect(JSON.parse(init.body)).toEqual({runIds:['a'.repeat(32)]});
 await expect(exportStandalone('revision',[])).rejects.toThrow('Missing wait evidence; recapture');
});
it('exports actual frontend-authored starter definitions and semantic data through the Python exporter',()=>{
 const w=template();w.nodes=w.nodes.filter(n=>['start','check-lambda','end'].includes(n.id));
 w.nodes[1].data.action='application';w.nodes.forEach(n=>n.data.config.retries=0);
 w.edges=[{id:'one',source:'start',target:'check-lambda'},{id:'two',source:'check-lambda',target:'end'}];
 const url='http://fixture:8080/';const wait={kind:'ready_region',timeout:10};
 w.nodes[1].data.config.replay={version:'sre-replay-task/v1',synthetic:true,steps:[
  {op:'navigate',url,pre_url:url,post_url:url,wait},
  {op:'assert_text',id:'status',text:'Synthetic replay complete',pre_url:url,post_url:url,wait}
 ]};
 const code='import json,sys; from triage.dag import DAG; from triage.standalone import export_spec; d=DAG.from_spec(json.load(sys.stdin)); print(json.dumps(export_spec(d,"a"*64,["http://fixture:8080/"])))';
 const result=spawnSync('python3',['-c',code],{cwd:fileURLToPath(new URL('../..',import.meta.url)),input:JSON.stringify(buildDAG(w)),encoding:'utf8'});
 expect(result.status,result.stderr).toBe(0);const spec=JSON.parse(result.stdout);
 expect(spec.tasks[0].id).toBe('check-lambda');expect(spec.tasks[0].steps.map(s=>s.op)).toEqual(['navigate','assert_text']);
});
