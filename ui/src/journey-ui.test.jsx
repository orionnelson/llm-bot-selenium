import {it,expect,vi,afterEach} from 'vitest';
import {renderToString} from 'react-dom/server';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import JourneyRecorder,{JourneyInstructions,startJourney} from './JourneyRecorder';
import {useJourneyDraft,or9Steps} from './journey-state';
import {useGrid} from './grid-state';
import {fromDAG} from './dag';
vi.mock('./grid-state',async original=>{const actual=await original();return {useGrid:Object.assign((selector)=>selector?selector(actual.useGrid.getState()):actual.useGrid.getState(),actual.useGrid)};});
afterEach(()=>vi.unstubAllGlobals());
it('keeps URL/Record/session playback on the right and human instruction steps outside the frame',()=>{
 useJourneyDraft.setState({url:'https://or9.ca/',steps:[...or9Steps]});useGrid.setState({run:undefined,history:[]});
 const instructions=renderToString(<JourneyInstructions/>),session=renderToString(<JourneyRecorder onPlan={()=>{}} notify={()=>{}}/>);
 expect(instructions.match(/<textarea/g)).toHaveLength(3);expect(instructions).toContain('One action per instruction · one DAG step');
 expect(session).toContain('Session URL');expect(session).toContain('● Record');expect(session).toContain('Your browser session appears here');
 for(const text of ['<textarea','Approve saved','Grid ready','Browser test mode','LLM Reasoning','Debugger'])expect(session).not.toContain(text);
});
it('maps actual server instruction DAGs to one dashboard node per instruction, without changing canonical saved tasks',()=>{
 const result=spawnSync('python3',['-c',"import json;from triage.journey import definition;print(json.dumps(definition('https://or9.ca/',['Find Projects','Click News','Screenshot article counts'])))"],{cwd:fileURLToPath(new URL('../..',import.meta.url)),encoding:'utf8'});
 expect(result.status,result.stderr).toBe(0);const workflow=fromDAG(JSON.parse(result.stdout));
 expect(workflow.nodes.map(n=>n.id)).toEqual(['start','navigate','step-1','step-2','step-3','end']);
 expect(workflow.nodes.find(n=>n.id==='step-2')?.data.config.prompt).toBe('Click News');expect(workflow.edges).toHaveLength(5);
});
it('sends the public URL and each instruction as bounded journey input, not a generated script or pretend recording',async()=>{
 const id='b'.repeat(32),fetch=vi.fn().mockResolvedValue({ok:true,json:async()=>({id,definition:{version:'sre-dag/v1'}})});vi.stubGlobal('fetch',fetch);
 expect((await startJourney('https://allenfort.ca/',['Screenshot the homepage'])).id).toBe(id);
 const [url,request]=fetch.mock.calls[0];expect(url).toBe('/api/browser/journeys');expect(JSON.parse(request.body)).toEqual({url:'https://allenfort.ca/',steps:['Screenshot the homepage']});
 await expect(startJourney('https://or9.ca/',[''])).rejects.toThrow('Fill in');expect(fetch).toHaveBeenCalledTimes(1);
});
it('shows the generated function and verified article excerpts, without claiming unrestricted Python execution',()=>{
 const id='d'.repeat(32),asset=`/api/browser/runs/${id}/frame-00.png`;
 useGrid.setState({history:[],run:{id,version:'browser-run/v1',taskId:'journey',status:'passed',startedAt:new Date().toISOString(),url:'https://or9.ca/',modelCalls:2,model:'local coder',evidenceKind:'simulated',frames:[asset],steps:[{id:'step-1',label:'Read News',action:'read',state:'verified',before:asset,videoMs:0,generatedPython:'def run(browser):\n    browser.read_articles("page-hash")',result:'Observed article',articles:[{title:'Security bulletin',url:'https://or9.ca/news',text:'Actual visible excerpt.'}]}],triage:{events:[]}}});
 const html=renderToString(<JourneyRecorder onPlan={()=>{}} notify={()=>{}}/>);
 expect(html).toContain('Generated functional code');expect(html).toContain('browser.read_articles');expect(html).toContain('Actual visible excerpt.');expect(html).toContain('not a full linked-article read');expect(html).toContain('not unrestricted Python');
 useGrid.setState({run:undefined,history:[]});
});
