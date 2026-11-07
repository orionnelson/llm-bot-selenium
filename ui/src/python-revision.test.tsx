import { afterEach, expect, it, vi } from 'vitest';
import { isValidElement, type ReactElement } from 'react';
import PythonInspector from './PythonInspector';
import { template } from './sre';
const state=vi.hoisted(()=>({setters:[] as ReturnType<typeof vi.fn>[]}));
vi.mock('react',async original=>({...await original<object>(),useRef:(value:unknown)=>({current:value}),useEffect:()=>{},useState:(value:unknown)=>{const set=vi.fn();state.setters.push(set);return [value,set];}}));
afterEach(()=>{vi.unstubAllGlobals();state.setters=[];});
function buttons(element:unknown):ReactElement<any>[] {
 if(!isValidElement(element))return [];
 const e=element as ReactElement<any>;
 return [e,...[e.props.children].flat(Infinity).flatMap(buttons)];
}
it.each(['saved-revision',null])('sends only the loaded revision (%s) with the actual generation callback',async revision=>{
 const update=vi.fn(),notify=vi.fn(),fetch=vi.fn(async(_url:string,_init:RequestInit)=>new Response(JSON.stringify({source:'def run(inputs, context=None):\n    return {}',model:'synthetic-model-double'}),{status:200}));
 vi.stubGlobal('fetch',fetch);
 const tree=PythonInspector({node:template().nodes[1],update,notify,revision});
 await buttons(tree).find(e=>e.type==='button'&&e.props.onClick?.name==='generate')!.props.onClick();
 const init=fetch.mock.calls[0][1] as {headers:Record<string,string>;body:string};
 expect(init.headers['If-Match']).toBe(revision??undefined);
 expect(init.body).not.toContain('saved-revision');
 expect(update).toHaveBeenCalledWith({python:expect.objectContaining({origin:'llm',review:'pending'})});
});
it('shows stale-DAG recovery instructions without applying a candidate',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({error:'DAG changed'}),{status:409})));
 const update=vi.fn();const tree=PythonInspector({node:template().nodes[1],update,notify:vi.fn(),revision:'obsolete'});
 await buttons(tree).find(e=>e.type==='button'&&e.props.onClick?.name==='generate')!.props.onClick();
 expect(update).not.toHaveBeenCalled();
 expect(state.setters.at(-1)).toHaveBeenCalledWith(expect.stringContaining('Load the current DAG'));
});
