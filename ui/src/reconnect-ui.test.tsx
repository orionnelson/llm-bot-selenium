import { expect,it,vi } from 'vitest';
import { renderToString } from 'react-dom/server';
import { ReactFlowProvider } from '@xyflow/react';
import { useStudio } from './store';
import { template, makeRun } from './sre';
import App from './App';
vi.mock('./store',async original=>{const actual=await original<typeof import('./store')>();return {useStudio:Object.assign(()=>actual.useStudio.getState(),actual.useStudio)};});
const captured=vi.hoisted(()=>({props:{} as any}));
vi.mock('@xyflow/react',async original=>({...await original<object>(),ReactFlow:(props:any)=>{captured.props=props;return null;}}));
it('wires left-end dragging to disconnection, atomic reconnection and undo',()=>{
 const w=template();useStudio.setState({workflow:w,past:[],future:[],mode:'Demo',run:undefined});
 renderToString(<ReactFlowProvider><App/></ReactFlowProvider>);
 const props=captured.props,edge=w.edges[0];
 expect(props.edgesReconnectable).toBe(true);expect(props.reconnectRadius).toBe(12);
 expect(props.edges[0].reconnectable).toBe('target');expect(props.edges[0].zIndex).toBe(1001);
 class CanvasElement{classList={contains:(name:string)=>name==='react-flow__pane'};}
 vi.stubGlobal('Element',CanvasElement);
 try{
  // Dropping on a node (including invalid input) is not a disconnect.
  props.onReconnectEnd({target:new CanvasElement()},edge,'source',{toNode:{id:'end'}});
  expect(useStudio.getState().workflow).toEqual(w);
  props.onReconnectEnd({target:new CanvasElement()},edge,'source',{toNode:null});
  expect(useStudio.getState().workflow.edges).toHaveLength(w.edges.length-1);
  useStudio.getState().undo();expect(useStudio.getState().workflow).toEqual(w);
  props.onReconnect(edge,{source:edge.source,sourceHandle:edge.sourceHandle??null,target:'summary',targetHandle:null});
  expect(useStudio.getState().workflow.edges.find(e=>e.id===edge.id)?.target).toBe('summary');
  useStudio.getState().undo();expect(useStudio.getState().workflow).toEqual(w);
 }finally{vi.unstubAllGlobals();}
});

it('disables input reconnection in recorded replay and ignores stale UI callbacks',()=>{
 const w=template();useStudio.setState({workflow:w,past:[],future:[],mode:'Replay',run:makeRun(w,'errors')});
 renderToString(<ReactFlowProvider><App/></ReactFlowProvider>);
 const props=captured.props;expect(props.edgesReconnectable).toBe(false);expect(props.edges.every((e:any)=>e.reconnectable===false)).toBe(true);
 props.onReconnect(w.edges[0],{source:'start',sourceHandle:null,target:'summary',targetHandle:null});
 props.onReconnectEnd({},w.edges[0],'source',{toNode:null});
 expect(useStudio.getState().workflow).toEqual(w);expect(useStudio.getState().past).toEqual([]);
 useStudio.setState({mode:'Demo',run:undefined});
});

it('retains controlled wire selection so Delete and the disconnect button can remove it',()=>{
 const w=template();useStudio.setState({workflow:w,past:[],future:[],mode:'Demo',run:undefined});
 const html=renderToString(<ReactFlowProvider><App/></ReactFlowProvider>);
 const props=captured.props,edge=w.edges[0];
 expect(html).toContain('Disconnect selected');
 props.onEdgesChange([{id:edge.id,type:'select',selected:true}]);
 props.onNodesChange([{id:w.nodes[0].id,type:'select',selected:false}]);
 expect(useStudio.getState().workflow.edges[0].selected).toBe(true);
 expect(useStudio.getState().past).toHaveLength(0);
 const nodes=useStudio.getState().workflow.nodes;
 props.onEdgesDelete([edge]);
 expect(useStudio.getState().workflow.edges.map(e=>e.id)).not.toContain(edge.id);
 expect(useStudio.getState().workflow.nodes).toEqual(nodes);
 useStudio.getState().undo();expect(useStudio.getState().workflow.edges).toHaveLength(w.edges.length);
 useStudio.setState({mode:'Replay',run:makeRun(w,'errors')});
 const before=useStudio.getState().workflow;
 props.onEdgesDelete([edge]);
 expect(useStudio.getState().workflow).toEqual(before);
 useStudio.setState({mode:'Demo',run:undefined});
});
