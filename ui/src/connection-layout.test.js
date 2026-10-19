import { readFileSync } from 'node:fs';
import { expect, it } from 'vitest';
it('keeps connection handles unclipped and provides a useful hit target',()=>{
 const css=readFileSync(new URL('./styles.css',import.meta.url),'utf8');
 expect(css.match(/\.node-card\{([^}]+)\}/)?.[1]).toContain('overflow:visible');
 expect(css.match(/\.react-flow__handle\{([^}]+)\}/)?.[1]).toContain('width:16px');
});
