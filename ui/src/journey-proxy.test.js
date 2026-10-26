import {it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
it('exposes journey API without permitting arbitrary proxy routes or recording files',()=>{
 const source=readFileSync(new URL('../serve-studio.ts',import.meta.url),'utf8');
 const pattern=source.match(/const api=(\/\^.+\$\/);/)[1],route=new RegExp(pattern.slice(1,-1));
 for(const path of ['/api/browser/journeys','/api/browser/runs','/api/browser/runs/'+'a'.repeat(32),'/api/browser/runs/'+'a'.repeat(32)+'/frame-02.png'])expect(route.test(path)).toBe(true);
 for(const path of ['/api/proxy','/api/browser/runs/../secret','/api/browser/runs/'+'a'.repeat(32)+'/manifest.json'])expect(route.test(path)).toBe(false);
 expect(source).toContain("Private studio password file required");expect(source).toContain("request.headers.get('origin')!==url.origin");expect(source).toContain("hosts.includes(url.hostname)");
});
