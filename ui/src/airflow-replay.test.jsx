import { expect, it } from 'vitest';
import { renderToString } from 'react-dom/server';
import { readFileSync } from 'node:fs';
import DAGInspector from './DAGInspector';
import { template } from './sre';

it('exposes consent and disabled Airflow controls in the normal DAG inspector',()=>{
 const html=renderToString(<DAGInspector workflow={template()}/>);
 expect(html).toContain('Airflow fast replay');
 expect(html).toContain('Disabled / not configured');
 expect(html).toContain('I reviewed the saved serial DAG');
 expect(html).toContain('I approve synthetic-only replay');
 expect(html).toContain('Save reviewed immutable artifact');
 expect(html).toContain('Select reviewed snapshot');
});

it('allows only hash-bound replay routes through the existing authenticated Bun proxy',()=>{
 const source=readFileSync(new URL('../serve-studio.ts',import.meta.url),'utf8');
 const match=source.match(/const api=\/(.+)\/;/);
 expect(match).not.toBeNull();
 const routes=new RegExp(match[1]),id='a'.repeat(64);
 for(const path of ['/api/dag/export/selenium','/api/airflow/artifacts',...['run','status','tasks','logs','stop'].map(op=>`/api/airflow/artifacts/${id}/${op}`)])expect(routes.test(path),path).toBe(true);
 for(const path of ['/api/airflow/credentials','/api/airflow/artifacts/../../run','/api/airflow/artifacts/not-a-hash/run',`/api/airflow/artifacts/${id}/delete`,`/api/airflow/artifacts/${id}/run?code=evil`])expect(routes.test(path),path).toBe(false);
 expect(source.indexOf('timingSafeEqual(supplied,expected)')).toBeLessThan(source.indexOf('if(!api.test(url.pathname))'));
});


it('binds review approval to canonical data, recordings and exact fetched revision',()=>{
 const source=readFileSync(new URL('./AirflowReplay.tsx',import.meta.url),'utf8');
 expect(source).toContain('JSON.stringify([workflow,runIds])');
 expect(source).toContain('approval?.key===reviewKey');
 expect(source).toContain('approval?.revision!==saved.revision');
 expect(source).toContain('setApproval(null);setSynthetic(false)');
});
