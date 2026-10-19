import { describe, expect, it } from 'vitest';
import { renderToString } from 'react-dom/server';
import { ReactFlowProvider } from '@xyflow/react';
import App from './App';
import ControlFlowEditor from './ControlFlowEditor';
import TriageDesigner from './TriageDesigner';
import { loopTemplate } from './control';
import { fixtureSession, clipSession } from './snippets';
describe('actual component markup (SSR, not browser interaction acceptance)',()=>{
 it('renders all five accessible pane splitters and the Triage tab',()=>{const html=renderToString(<ReactFlowProvider><App/></ReactFlowProvider>);expect(html.match(/role="separator"/g)).toHaveLength(5);for(const label of ['Resize component library','Resize node inspector','Resize browser and workflow','Resize browser and debugger','Resize debugger and history'])expect(html).toContain(label);expect(html).toContain('Triage');});
 it('renders loop form, bounds, increment, cap and body/exit summaries',()=>{const workflow=loopTemplate();const node=workflow.nodes.find(n=>n.data.action==='loop')!;node.data.config.loop!.mode='while';const html=renderToString(<ControlFlowEditor node={node} workflow={workflow} update={()=>{}}/>);for(const field of ['Loop form','Loop variable','Loop start','While operator','Loop step','Loop iteration limit'])expect(html).toContain(field);expect(html).toContain('BODY');expect(html).toContain('DONE');});
 it('does not invent an attached live session and renders reusable snippet entries',()=>{const clip=clipSession(fixtureSession(),0,2,'Saved investigation');const html=renderToString(<TriageDesigner snippets={[clip]} onSave={()=>{}} onUse={()=>{}} notify={()=>{}}/>);expect(html).toContain('No triage session attached');expect(html).toContain('Saved investigation');expect(html).toContain('Add snippet node to canvas');expect(html).toContain('Live transport');});
});
