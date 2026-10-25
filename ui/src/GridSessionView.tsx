import { useEffect, useState, useRef } from 'react';
import { activeRun, recordingAsset, type BrowserRun } from './browser';

export default function GridSessionView({run,compact=false,focusFrame,onFrame}:{run:BrowserRun;compact?:boolean;focusFrame?:number;onFrame?:(ms:number)=>void}){
 const callback=useRef(onFrame);callback.current=onFrame;
 const live=activeRun(run),[index,setIndex]=useState(Math.max(0,run.frames.length-1)),[playing,setPlaying]=useState(false);
 const wasLive=useRef(live);
 useEffect(()=>{setIndex(Math.max(0,run.frames.length-1));setPlaying(false);},[run.id]);
 useEffect(()=>{if(wasLive.current&&!live)setIndex(Math.max(0,run.frames.length-1));wasLive.current=live;},[live]);
 useEffect(()=>{if(focusFrame!==undefined){setIndex(focusFrame);setPlaying(false);}},[focusFrame]);
 useEffect(()=>{callback.current?.(run.frameTimesMs?.[live?run.frames.length-1:index]??0);},[index,live,run.id,run.frames.length]);
 useEffect(()=>{
  if(!playing||live||run.frames.length<2)return;
  if(index>=run.frames.length-1){setPlaying(false);return;}
  const times=run.frameTimesMs??[],delay=Math.max(50,(times[index+1]??(index+1)*500)-(times[index]??index*500));
  const timer=setTimeout(()=>setIndex(i=>i+1),delay);return()=>clearTimeout(timer);
 },[playing,live,index,run.id,run.frames.length]);
 const selected=live?run.frames.length-1:Math.min(index,run.frames.length-1),image=run.frames[selected];
 return <section aria-label="Grid session viewer">{!compact&&<h4>{live?'LIVE Grid session':'Recorded Grid session'} · {run.phase??run.status}</h4>}
 {!compact&&<p>{live?'Auto-refreshing the actual Edge session.':'Replay of timestamped frames from the actual Edge session.'} View-only, approximately 2 frames/second; not a continuous screen video.</p>}
 {image?<img className="browser-run-frame" src={recordingAsset(image)} alt={live?'Live Edge session frame':'Recorded Edge session frame'}/>:<p>Waiting for the Grid browser to open…</p>}
 <p>{run.frames.length} recorded frames · {((run.frameTimesMs?.[selected]??0)/1000).toFixed(1)}s</p>
 {!live&&run.frames.length>0&&<><button onClick={()=>{if(!playing&&index>=run.frames.length-1)setIndex(0);setPlaying(!playing);}}>{playing?'Pause session replay':'Play session replay'}</button><input aria-label="Session recording timeline" type="range" min={0} max={Math.max(0,run.frames.length-1)} value={Math.max(0,selected)} onChange={e=>{setPlaying(false);setIndex(Number(e.target.value));}}/></>}
 </section>;
}
