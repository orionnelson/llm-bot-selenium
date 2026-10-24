import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { expect, it } from 'vitest';
import { parseSession, clipSession } from './snippets';
import { config, template, validateFlow, makeRun, atTime } from './sre';
import { buildDAG, exportDAGPython } from './dag';

const root=fileURLToPath(new URL('../..',import.meta.url));
function exportedSession(){
 const code=`import json
from dataclasses import replace
from unittest.mock import Mock
from triage.chart_browser import SeleniumChartPort
from triage.chart_checks import ChartBinding, ChartView, SyntheticObserver
from triage.core import Action, Context
port = SeleniumChartPort(Mock(session_id='private-driver-id'), 'http://127.0.0.1:8765')
binding = ChartBinding(Context('synthetic', 'test', 'checkout', 0, 2000), Action('overview', 'invocation_health'), 'errors', 'percent')
view = ChartView(binding, 'private-evidence-id', 100, 100, 0)
observer = SyntheticObserver(port.session, [binding], consent=True)
observer.record('navigate', 'dashboard', view)
observer.record('shortcut-open-chart', 'entity-chart', replace(view, captured_at=102))
print(json.dumps(port.export_studio_session(observer.stop(), consent=True)))`;
 const result=spawnSync('python3',['-c',code],{cwd:root,encoding:'utf8'});
 expect(result.status,result.stderr).toBe(0);
 expect(result.stdout).not.toMatch(/private-driver-id|private-evidence-id|checkout/);
 return JSON.parse(result.stdout);
}
it('imports actual Python exporter output and preserves semantic shortcut, clip IDs and timestamps',()=>{
 const raw=exportedSession();const session=parseSession(raw);
 expect(session.provenance).toBe('imported');
 expect(session.events.map(e=>e.action)).toEqual(['navigate','shortcut-open-chart']);
 expect(session.events.map(e=>e.elapsedMs)).toEqual([0,2000]);
 const clip=clipSession(session,1,1,'Observed shortcut');
 expect(clip.steps[0]).toMatchObject({action:'shortcut-open-chart',elapsedMs:0,url:'http://127.0.0.1:8765/chart/entity-chart'});
 expect(clip.source.eventIds).toEqual([raw.events[1].id]);
 expect(clip.source.sessionId).toBe(raw.id);
});
it('roundtrips observer snippets in the active native graph and Python DAG without pretending to execute',()=>{
 const clip=clipSession(parseSession(exportedSession()),0,1,'Observed chart path');
 const w=template();w.nodes=[w.nodes[0],{id:'observed-path',type:'action',position:{x:200,y:100},data:{action:'snippet',label:clip.name,config:{...config(),snippet:clip}}}];
 w.edges=[{id:'path',source:'start',target:'observed-path'}];w.snippets=[clip];
 const saved=validateFlow(JSON.parse(JSON.stringify(w)));
 expect(saved.nodes[1].data.config.snippet).toEqual(clip);
 const run=makeRun(saved,'errors');expect(run.status).toBe('Pending');
 expect(atTime(run,run.duration).states['observed-path']).toBe('waiting');
 const result=spawnSync('python3',['-c','import sys,json; from triage.dag import load_python; print(json.dumps(load_python(sys.stdin.read()).to_spec()))'],{cwd:root,input:exportDAGPython(saved),encoding:'utf8'});
 expect(result.status,result.stderr).toBe(0);expect(JSON.parse(result.stdout)).toEqual(buildDAG(saved));
});
it('keeps rejecting raw keys and typed shortcut payloads at the Studio boundary',()=>{
 const session=exportedSession();
 for(const event of [{...session.events[1],action:'keydown'},{...session.events[1],keys:'Ctrl+secret'},{...session.events[1],value:'private'}]){
  expect(()=>parseSession({...session,events:[event]})).toThrow();
 }
});
