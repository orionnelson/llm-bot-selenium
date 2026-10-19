import { readFileSync } from 'node:fs';
import { expect, it } from 'vitest';
it('keeps connection handles unclipped and provides a useful hit target',()=>{
 const css=readFileSync(new URL('./styles.css',import.meta.url),'utf8');
 expect(css.match(/\.node-card\{([^}]+)\}/)?.[1]).toContain('overflow:visible');
 expect(css.match(/\.react-flow__handle\{([^}]+)\}/)?.[1]).toContain('width:16px');
});
it('reserves separate non-overlapping header columns and fills the entire node canvas',()=>{
 const css=readFileSync(new URL('./styles.css',import.meta.url),'utf8');
 expect(css).toContain('grid-template-columns:minmax(0,1fr) auto auto');
 expect(css).toContain('overflow-x:auto;overflow-y:hidden');
 expect(css).toContain('.workflow-canvas>.react-flow{position:absolute!important;inset:0;width:100%!important;height:100%!important}');
 expect(css).toContain('minmax(0,1fr) 6px var(--right)');
});
