import type {FlowNode} from './sre';
import { BaseEdge, EdgeLabelRenderer, type EdgeProps } from '@xyflow/react';

export function loopBounds(nodes:FlowNode[]){
 const left=Math.min(...nodes.map(n=>n.position.x))-35,top=Math.min(...nodes.map(n=>n.position.y));
 const right=Math.max(...nodes.map(n=>n.position.x+(n.measured?.width??(['start','end'].includes(n.data.action)?130:190))))+35;
 const repeatY=Math.max(...nodes.map(n=>n.position.y+(n.measured?.height??260)))+70;
 return {x:left,y:top,width:right-left,height:repeatY-top+40,repeatY};
}

// Route the repeat below every card, outside the source/target sides, rather than across their text.
export function loopReturnPath(sx:number,sy:number,tx:number,ty:number,bottom:number){
 return `M ${sx} ${sy} H ${sx+28} V ${bottom} H ${tx-28} V ${ty} H ${tx}`;
}
export default function LoopReturnEdge({id,sourceX,sourceY,targetX,targetY,data,style,markerEnd,selected}:EdgeProps){
 const bottom=typeof data?.routeY==='number'?data.routeY:Math.max(sourceY,targetY)+120;
 return <><BaseEdge id={id} path={loopReturnPath(sourceX,sourceY,targetX,targetY,bottom)} markerEnd={markerEnd} style={{...style,stroke:'#BA9CFF',strokeWidth:selected?3:2,strokeDasharray:'6 4'}}/>
 <EdgeLabelRenderer><span className="loop-return-label" style={{transform:`translate(-50%, -50%) translate(${(sourceX+targetX)/2}px, ${bottom}px)`}}>REPEAT</span></EdgeLabelRenderer></>;
}
