import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { expect, it } from 'vitest';
import { parseRun, recordingAsset, activeRun } from './browser';
import { clipSession, validateSnippet } from './snippets';
it('accepts actual Python action recording output and reuses its native triage events',()=>{
 const code=`import json,sys,tempfile
from pathlib import Path
from threading import Lock
from unittest.mock import patch
sys.path.insert(0,'tests')
from test_browser_loop import browser_dag,FakeDriver,choice
from triage.browser_loop import BrowserRuns
with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ',{'SELENIUM_GRID_URL':'http://selenium:4444'}), patch('triage.browser_loop.grid_status',return_value={'ready':True}), patch('triage.browser_loop.propose',side_effect=choice):
 runs=BrowserRuns(Path(directory),Lock(),lambda:'revision',driver_factory=lambda url:FakeDriver(),evidence_kind='simulated')
 queued=runs.start(browser_dag(),'revision','browser-check',True,False)
 assert runs.generation_lock.acquire(timeout=5)
 runs.generation_lock.release()
 print(json.dumps(runs.read(queued['id'])))
`;
 const result=spawnSync('python3',['-c',code],{cwd:fileURLToPath(new URL('../..',import.meta.url)),encoding:'utf8'});
 expect(result.status,result.stderr).toBe(0);const run=parseRun(JSON.parse(result.stdout));
 expect(run.status).toBe('passed');expect(run.evidenceKind).toBe('simulated');expect(activeRun(run)).toBe(false);
 expect(run.steps[0].state).toBe('verified');expect(run.frames).toHaveLength(2);
 const snippet=clipSession(run.triage,0,run.triage.events.length-1,'Recorded browser check');
 expect(validateSnippet(snippet).steps.map(s=>s.action)).toEqual(['navigate','click']);
 expect(snippet.source.provenance).toBe('imported');
});
it('rejects arbitrary asset URLs and traversal rather than embedding them',()=>{
 for(const value of ['https://evil.example/video.webm','file:///etc/passwd','/api/browser/runs/../secret','/api/browser/runs/'+'a'.repeat(32)+'/manifest.json'])expect(()=>recordingAsset(value)).toThrow();
 expect(recordingAsset('/api/browser/runs/'+'a'.repeat(32)+'/frame-00.png')).toContain('frame-00.png');
});
