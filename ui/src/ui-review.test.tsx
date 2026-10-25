import {expect,it} from 'vitest';
import {renderToString} from 'react-dom/server';
import {ReactFlowProvider} from '@xyflow/react';
import App from './App';
import DAGInspector from './DAGInspector';
import BrowserPolicyEditor from './BrowserPolicyEditor';
import {template} from './sre';
import {loopReturnPath,loopBounds} from './LoopReturnEdge';

it('routes repeat below the graph and outside both card sides',()=>{
 expect(loopReturnPath(1130,200,200,360,800)).toBe('M 1130 200 H 1158 V 800 H 172 V 360 H 200');
});
it('has one selected tab per group, keyboard-focusable active tabs and explicit inspector/import/history controls',()=>{
 const html=renderToString(<ReactFlowProvider><App/></ReactFlowProvider>);
 expect(html.match(/role="tablist"/g)).toHaveLength(2);
 expect(html.match(/aria-selected="true"/g)).toHaveLength(2);
 expect(html).toContain('Expand inspector');expect(html).toContain('Import workflow JSON file');
 expect(html).toContain('Demo history');expect(html).toContain('Export local workflow JSON');
});
it('labels draft browser policy as draft, not saved canonical state',()=>{
 const html=renderToString(<BrowserPolicyEditor nodeId="check-lambda"/>);
 expect(html).toContain('Current draft');expect(html).toContain('Changes remain local until Save');
 expect(html).not.toContain('Saved task ·');
});
it('stacks the DAG import guidance and points to a visible import control',()=>{
 const html=renderToString(<DAGInspector workflow={template()}/>);
 expect(html).toContain('dag-import-guidance');expect(html).toContain('bottom toolbar');
 expect(html).toContain('workflow.dag.json');expect(html).not.toContain('<p class="pending">');
});

it('includes the repeat line and its label in the fit bounds, not only node bounds',()=>{
 const w=template();const bounds=loopBounds(w.nodes);
 expect(bounds.y+bounds.height).toBeGreaterThan(bounds.repeatY);
 expect(bounds.x).toBeLessThan(Math.min(...w.nodes.map(n=>n.position.x)));
});
