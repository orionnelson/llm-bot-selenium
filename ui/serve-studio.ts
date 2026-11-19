// Authenticated LAN frontend; canonical Python/browser APIs remain loopback-only.
import { timingSafeEqual } from 'node:crypto';
import { resolve, extname } from 'node:path';
const root=resolve(process.env.SRE_TEMPLATE_ROOT||'/srv/opencode/data/opencode/tool-output/sre-grid-studio/ui-dist');
const backend=new URL(process.env.SRE_DAG_BACKEND_URL||'http://127.0.0.1:3033');
if(backend.origin!=='http://127.0.0.1:3033'||backend.pathname!=='/'||backend.search||backend.hash||backend.username)throw Error('Fixed loopback DAG backend required');
const passwordFile=process.env.SRE_STUDIO_PASSWORD_FILE;
if(!passwordFile)throw Error('Private studio password file required before LAN hosting');
const password=(await Bun.file(passwordFile).text()).trim();
if(password.length<24)throw Error('Studio password must contain at least 24 characters');
const expected=Buffer.from('Basic '+Buffer.from('blue-lagoon:'+password).toString('base64'));
const origins=process.env.SRE_STUDIO_ORIGINS?.split(',');
const hosts=['smol-kitten.local','smol-kitten','127.0.0.1','localhost','opencode-svc.llms.svc.cluster.local'];
const mime:Record<string,string>={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json','.svg':'image/svg+xml'};
const api=/^\/api\/(?:dag|test\/status|python\/generate|browser\/journeys|browser\/runs(?:\/[a-f0-9]{32}(?:\/(?:cancel|frame-\d{2}\.png|actions\.webm))?)?)$/;
function unauthorized(){return new Response('Studio sign-in required',{status:401,headers:{'WWW-Authenticate':'Basic realm="Edge Grid Studio", charset="UTF-8"','Cache-Control':'no-store'}});}
const server=Bun.serve({maxRequestBodySize:1000000,hostname:'0.0.0.0',port:Number(process.env.SRE_STUDIO_PORT||3002),async fetch(request:Request){
 const url=new URL(request.url);
 if(url.pathname==='/health'&&request.method==='GET')return Response.json({service:'sre-flow-studio',mode:'edge-grid',executionBackend:true});
 const supplied=Buffer.from(request.headers.get('authorization')||'');
 if(supplied.length!==expected.length||!timingSafeEqual(supplied,expected))return unauthorized();
 if(!(origins?origins.includes(url.origin):hosts.includes(url.hostname))||request.headers.has('origin')&&request.headers.get('origin')!==url.origin)return new Response('Origin denied',{status:403});
 if(url.search)return new Response('Query parameters are not supported',{status:400});
 if(url.pathname.startsWith('/api/')){
  if(!api.test(url.pathname))return new Response('Unknown API route',{status:404});
  if(!['GET','POST','PUT'].includes(request.method))return new Response('Method not allowed',{status:405});
  // Authenticate/check the external origin first; never forward credentials or untrusted Origin/Host.
  const headers=new Headers();for(const name of ['Content-Type','If-Match']){const value=request.headers.get(name);if(value)headers.set(name,value);}
  try{
   const body=['POST','PUT'].includes(request.method)?await request.arrayBuffer():undefined;
   if(body&&body.byteLength>1000000)return new Response('Request too large',{status:413});
   const response=await fetch(new URL(url.pathname,backend),{method:request.method,headers,body,redirect:'error',signal:AbortSignal.timeout(url.pathname==='/api/python/generate'?240000:20000)});
   return new Response(response.body,{status:response.status,headers:response.headers});
  }catch{return Response.json({error:'Python Grid backend unavailable; no result claimed'},{status:502});}
 }
 if(!['GET','HEAD'].includes(request.method))return new Response('Method not allowed',{status:405});
 let path:string;try{path=decodeURIComponent(url.pathname);}catch{return new Response('Bad path',{status:400});}
 if(path==='/')path='/index.html';const file=resolve(root,'.'+path);
 if(!file.startsWith(root+'/')||path.includes('\0'))return new Response('Forbidden',{status:403});
 const asset=Bun.file(file);if(!await asset.exists())return new Response('Not found',{status:404});
 return new Response(request.method==='HEAD'?null:asset,{headers:{'Content-Type':mime[extname(file)]||'application/octet-stream','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Cache-Control':'no-store','Content-Security-Policy':"default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"}});
}});
console.log(`Authenticated Edge Grid Studio listening on ${server.port}`);

