import { afterEach, expect, it, vi } from 'vitest';
vi.mock('./grid-state',async original=>{const actual=await original<typeof import('./grid-state')>();return {...actual,useGrid:Object.assign((selector?:any)=>selector?selector(actual.useGrid.getState()):actual.useGrid.getState(),actual.useGrid)};});
vi.mock('./store',async original=>{const actual=await original<typeof import('./store')>();return {...actual,useStudio:Object.assign((selector?:any)=>selector?selector(actual.useStudio.getState()):actual.useStudio.getState(),actual.useStudio)};});
import { renderToString } from 'react-dom/server';
import { useGrid, gridStatus } from './grid-state';
import { GridDebug, GridFrame, GridHistory } from './GridEvidence';
import BrowserPolicyEditor from './BrowserPolicyEditor';
import { useStudio } from './store';
import { template } from './sre';
import { buildDAG, fromDAG } from './dag';
import type { BrowserRun } from './browser';
const run:BrowserRun={version:'browser-run/v1',id:'a'.repeat(32),taskId:'check-lambda',status:'running',evidenceKind:'simulated',startedAt:'2026-10-24T00:00:00Z',url:'https://or9.ca/',model:'none',modelCalls:0,frames:[],steps:[],policy:{mode:'read-only-or9'},triage:{version:'triage-session/v1',id:'triage',mode:'recorded',provenance:'imported',url:'https://or9.ca/',events:[]}};
const status={mode:'test',grid:{ready:true,status:'reachable',edgeAvailable:true,browsers:['MicrosoftEdge'],nodes:1},modelBusy:false,approvedUrls:['https://or9.ca/'],videoAvailable:false};
afterEach(()=>{vi.unstubAllGlobals();useGrid.setState({run:undefined,history:[],status:undefined,error:'',view:'grid'});useStudio.setState({workflow:template(),mode:'Demo'});});
it('restores active backend runs and surfaces connection failure rather than leaving stale readiness',async()=>{
 vi.stubGlobal('fetch',vi.fn(async(path:string)=>Response.json(path==='/api/test/status'?status:[run])));
 await useGrid.getState().refresh();expect(useGrid.getState().run?.id).toBe(run.id);expect(useGrid.getState().status?.grid.edgeAvailable).toBe(true);
 vi.stubGlobal('fetch',vi.fn(async()=>new Response('',{status:503})));
 await useGrid.getState().refresh();expect(useGrid.getState().status).toBeUndefined();expect(useGrid.getState().error).toContain('unavailable');
});
it('rejects static-host and malformed health responses',async()=>{
 for(const body of [{service:'sre-flow-template'}, {...status,approvedUrls:[42]}]){
  vi.stubGlobal('fetch',vi.fn(async()=>Response.json(body)));await expect(gridStatus()).rejects.toThrow('Invalid Grid backend response');
 }
});
it('opens real backend history without triggering browser execution',async()=>{
 const fetch=vi.fn(async(_path:string)=>Response.json({...run,status:'passed'}));vi.stubGlobal('fetch',fetch);
 await useGrid.getState().open(run.id);expect(fetch).toHaveBeenCalledOnce();expect(fetch.mock.calls[0][0]).toBe('/api/browser/runs/'+run.id);expect(useGrid.getState().view).toBe('grid');expect(useGrid.getState().run?.status).toBe('passed');
});
it('renders Grid logs, proposals, navigation, frames and history from shared run state, never fixture success',()=>{
 useGrid.setState({run:{...run,status:'failed',error:'SessionNotCreatedException',reason:'Edge could not start'},history:[run]});
 expect(renderToString(<GridDebug tab="Logs"/>)).toContain('Edge could not start');
 expect(renderToString(<GridDebug tab="LLM Reasoning"/>)).toContain('No model call was made');
 expect(renderToString(<GridDebug tab="Network"/>)).toContain('not HTTP traffic capture');
 expect(renderToString(<GridDebug tab="Screenshots"/>)).toContain('No screenshots captured');
 expect(renderToString(<GridFrame/>)).toContain('intentionally do not capture');
 expect(renderToString(<GridHistory open={()=>{}}/>)).toContain('running');
});
it('keeps authorable browser policies through actual DAG projection and disables replay editing',()=>{
 const workflow=template();workflow.nodes[1].data.config.browser={mode:'read-only-or9'};workflow.nodes[1].data.config.target='https://or9.ca/';
 const projected=fromDAG(buildDAG(workflow));expect(projected.nodes.find(n=>n.id===workflow.nodes[1].id)?.data.config.browser).toEqual({mode:'read-only-or9'});
 useStudio.setState({workflow:projected,mode:'Replay'});
 const html=renderToString(<BrowserPolicyEditor nodeId={workflow.nodes[1].id}/>);expect(html).toContain('Browser test mode');expect(html).toContain('or9.ca');expect(html).toContain('<fieldset disabled=""');
});
