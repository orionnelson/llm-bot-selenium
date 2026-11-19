import {create} from 'zustand';
export const or9Steps=['Find the Projects section.','Click Security News to expand its dropdown.','Read the visible article headlines and excerpts in Security News.'];
interface Draft {url:string;steps:string[];playbackMs:number|null;setUrl:(url:string)=>void;setSteps:(steps:string[])=>void;seek:(ms:number|null)=>void}
export const useJourneyDraft=create<Draft>(set=>({url:'https://or9.ca/',steps:[...or9Steps],playbackMs:null,setUrl:url=>set({url}),setSteps:steps=>set({steps}),seek:playbackMs=>set({playbackMs})}));
