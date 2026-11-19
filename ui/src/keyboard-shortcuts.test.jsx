// Actual component handlers/effects in a hook harness; parent owns browser acceptance.
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import App from './App';
import {useStudio} from './store';
import {useGrid} from './grid-state';
import {useJourneyDraft} from './journey-state';
import {template} from './sre';

const h=vi.hoisted(()=>({cells:[],effects:[],queue:[],cursor:0,dirty:false,beforeEffects:null,keys:new Map(),flow:{fitView:vi.fn(),fitBounds:vi.fn(),getNodesBounds:vi.fn(()=>({x:0,y:0,width:805,height:370})),zoomIn:vi.fn(),zoomOut:vi.fn(),screenToFlowPosition:vi.fn(point=>point)}}));
vi.mock('react',async original=>({...await original(),
 useState(initial){const i=h.cursor++;if(!(i in h.cells))h.cells[i]=typeof initial==='function'?initial():initial;return [h.cells[i],value=>{const next=typeof value==='function'?value(h.cells[i]):value;if(!Object.is(next,h.cells[i])){h.cells[i]=next;h.dirty=true;}}];},
 useRef(initial){const i=h.cursor++;return h.cells[i]??(h.cells[i]={current:initial});},
 useCallback(fn,deps){const i=h.cursor++,old=h.cells[i];if(!old||deps.some((v,j)=>!Object.is(v,old.deps[j])))h.cells[i]={fn,deps};return h.cells[i].fn;},
 useImperativeHandle(){},
 useEffect(effect,deps){const i=h.cursor++,old=h.effects[i];if(!old||!deps||deps.some((v,j)=>!Object.is(v,old.deps[j])))h.queue.push(()=>{old?.cleanup?.();h.effects[i]={deps,cleanup:effect()};});},
}));
vi.mock('@xyflow/react',async original=>({...await original(),ReactFlow:'flow-harness',useReactFlow:()=>h.flow,useNodesInitialized:()=>true}));
vi.mock('./store',async original=>{const m=await original();return {...m,useStudio:Object.assign(selector=>selector?selector(m.useStudio.getState()):m.useStudio.getState(),m.useStudio)};});
vi.mock('./grid-state',async original=>{const m=await original();return {...m,useGrid:Object.assign(selector=>selector?selector(m.useGrid.getState()):m.useGrid.getState(),m.useGrid)};});
vi.mock('./journey-state',async original=>{const m=await original();return {...m,useJourneyDraft:Object.assign(selector=>selector?selector(m.useJourneyDraft.getState()):m.useJourneyDraft.getState(),m.useJourneyDraft)};});
function render(component,props={}){let tree,count=0;do{h.dirty=false;h.cursor=0;tree=component(props);h.beforeEffects?.(tree);h.queue.splice(0).forEach(effect=>effect());if(++count>20)throw Error('Unstable hooks');}while(h.dirty);return tree;}
function reset(){h.effects.forEach(e=>e?.cleanup?.());h.cells=[];h.effects=[];h.queue=[];h.cursor=0;h.dirty=false;}
let unsubscribe;
beforeEach(()=>{
 vi.useFakeTimers();h.beforeEffects=null;h.flow.viewportInitialized=true;h.flow.fitView.mockReset();h.flow.fitBounds.mockReset();h.flow.zoomIn.mockClear();h.flow.zoomOut.mockClear();h.keys.clear();
 const workflow={...template(),name:'Canonical actual source · unsaved owner edits'};
 useStudio.setState({workflow,selected:'check-lambda',past:[template()],future:[template()],run:undefined,playing:false,mode:'Demo'});
 useGrid.setState({view:'grid',run:undefined,history:[]});useJourneyDraft.setState({editedRecordingId:null,requestedStepId:null,playbackStepId:null});
 unsubscribe=useStudio.subscribe(()=>{h.dirty=true;});
 vi.stubGlobal('window',{innerWidth:1400,innerHeight:900,addEventListener:(name,fn)=>h.keys.set(name,fn),removeEventListener:(name,fn)=>{if(h.keys.get(name)===fn)h.keys.delete(name);}});
 vi.stubGlobal('localStorage',{getItem:vi.fn(()=>null),setItem:vi.fn()});
 vi.stubGlobal('requestAnimationFrame',vi.fn(callback=>{callback(0);return 1;}));vi.stubGlobal('cancelAnimationFrame',vi.fn());
 vi.stubGlobal('fetch',vi.fn(async()=>{throw Error('offline fixture');}));
});
afterEach(()=>{unsubscribe?.();reset();vi.restoreAllMocks();vi.useRealTimers();vi.unstubAllGlobals();});

it.each(['button','a[href]','summary','[role="button"]','[role="tab"]','[role="link"]','input','textarea','select','[contenteditable="true"]'])('leaves native and descendant %s keyboard events untouched',selector=>{
 render(App);const seek=vi.spyOn(useStudio.getState(),'seek'),closest=vi.fn(query=>query.split(',').includes(selector)?{}:null),preventDefault=vi.fn();
 for(const key of [' ','ArrowRight','ArrowLeft','Home','End','k','l']){
  const before=useStudio.getState();h.keys.get('keydown')({key,target:{closest},preventDefault});
  expect(useStudio.getState().playing).toBe(before.playing);expect(useStudio.getState().clock).toBe(before.clock);
 }
 expect(preventDefault).not.toHaveBeenCalled();expect(seek).not.toHaveBeenCalled();
});
it('respects a child-handled key before touching demo playback or clock',()=>{
 render(App);const before=useStudio.getState(),seek=vi.spyOn(before,'seek'),closest=vi.fn(),preventDefault=vi.fn();
 for(const key of [' ','ArrowRight','ArrowLeft','Home','End'])h.keys.get('keydown')({key,defaultPrevented:true,target:{closest},preventDefault});
 expect(useStudio.getState().playing).toBe(before.playing);expect(useStudio.getState().clock).toBe(before.clock);expect(closest).not.toHaveBeenCalled();expect(preventDefault).not.toHaveBeenCalled();expect(seek).not.toHaveBeenCalled();
});
it('retains the background demo Space shortcut and canvas Space panning',()=>{
 render(App);const preventDefault=vi.fn();h.keys.get('keydown')({key:' ',target:{closest:()=>null},preventDefault});
 expect(useStudio.getState().playing).toBe(true);expect(preventDefault).toHaveBeenCalledOnce();render(App);
 h.keys.get('keydown')({key:' ',target:{closest:query=>query==='.workflow-canvas'?{}:null},preventDefault});
 expect(useStudio.getState().playing).toBe(true);expect(preventDefault).toHaveBeenCalledOnce();
});

it('preserves App Escape and explicit Ctrl+S when a button has focus',()=>{
 render(App);const closest=query=>query.split(',').includes('button')?{}:null,preventDefault=vi.fn();
 h.keys.get('keydown')({key:'Escape',target:{closest},preventDefault});expect(useStudio.getState().selected).toBe('');render(App);
 h.keys.get('keydown')({key:'s',ctrlKey:true,target:{closest},preventDefault});expect(preventDefault).toHaveBeenCalledOnce();expect(localStorage.setItem).toHaveBeenCalled();
});
