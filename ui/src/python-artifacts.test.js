import { spawnSync } from 'node:child_process';
import { expect, it } from 'vitest';
import { template } from './sre';
import { starterPython, exportPython, defaultCondition } from './python';
it('all frontend-generated Python artifacts parse in real Python without executing them',()=>{
 const w=template();w.nodes.find(n=>n.data.action==='condition').data.config.condition={...defaultCondition};w.nodes[1].data.config.target='quoted "target"\nwith unicode λ';
 const sources=[...w.nodes.map(starterPython),exportPython(w.nodes)];
 const result=spawnSync('python3',['-c','import ast,json,sys; sources=json.load(sys.stdin); [ast.parse(s) for s in sources]; print(len(sources))'],{input:JSON.stringify(sources),encoding:'utf8'});
 expect(result.status,result.stderr).toBe(0);expect(result.stdout.trim()).toBe('9');
});
