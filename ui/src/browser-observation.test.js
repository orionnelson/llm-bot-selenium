import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { describe, expect, it } from 'vitest';

// Execute the actual injected script against a small DOM test double, not a browser.
const source = readFileSync(new URL('../../triage/browser_loop.py', import.meta.url), 'utf8');
const script = source.match(/OBSERVE = r"""([\s\S]*?)"""/)[1];
function element(tag = 'div', attributes = {}, children = []) {
  const node = {
    tagName: tag.toUpperCase(), attributes, children,
    getAttribute(name) { return this.attributes[name] ?? null; },
    checkVisibility() { return true; },
    closest(selector) {
      for (let current = this; current; current = current.parentElement) {
        if (selector.split(',').some(s => {
          s = s.trim();
          if (!s.startsWith('[')) return current.tagName.toLowerCase() === s;
          const [, key, value] = s.match(/^\[([^=\]]+)(?:="([^"]*)")?\]$/);
          return key in current.attributes && (value === undefined || current.attributes[key] === value);
        })) return current;
      }
      return null;
    },
    querySelectorAll(selector) {
      return descendants(this).filter(n => n.tagName && n.closest(selector) === n);
    },
    get innerText() { return descendants(this).filter(n => !n.tagName).map(n => n.textContent).join(' '); },
  };
  node.children = children.map(c => typeof c === 'string' ? { textContent: c } : c);
  node.children.forEach(c => { c.parentElement = node; });
  return node;
}
function descendants(node) { return node.children.flatMap(c => [c, ...(c.children ? descendants(c) : [])]); }
function observe(result) {
  const root = element('section', { 'data-sre-observe': '' }, [result]);
  const document = { createTreeWalker(node) {
    const nodes = descendants(node).filter(n => !n.tagName); let index = 0;
    return { nextNode: () => nodes[index++] ?? null };
  } };
  return runInNewContext(`(function(){${script}})`, { document, NodeFilter: { SHOW_TEXT: 4 } })(root, 'errors');
}

describe('consented observation text (simulated DOM)', () => {
  it.each(['data-private', 'hidden', 'aria-hidden', 'contenteditable'])('excludes %s descendants from result and page evidence', attribute => {
    const result = element('div', { 'data-sre-result': 'errors' }, [
      'Errors: 0', element('span', { [attribute]: attribute === 'aria-hidden' ? 'true' : '' }, ['FAKE_PRIVATE_VALUE']),
    ]);
    const value = observe(result);
    expect(value.result).toBe('Errors: 0');
    expect(value.text).toBe('Errors: 0');
    expect(JSON.stringify(value)).not.toContain('FAKE_PRIVATE_VALUE');
  });
  it('excludes form contents from the result', () => {
    expect(observe(element('div', { 'data-sre-result': 'errors' }, [
      'Errors: 0', element('form', {}, ['NOT_A_REAL_PASSWORD']),
    ])).result).toBe('Errors: 0');
  });
  it.each(['result', 'label', 'page'])('flags incomplete %s evidence when the traversal budget is exhausted', kind => {
    const attrs = kind === 'result' ? { 'data-sre-result': 'errors' }
      : kind === 'label' ? { 'data-sre-action': 'show-errors', 'data-sre-safe': 'true' } : {};
    const limit = kind === 'label' ? 500 : 5000;
    const value = observe(element(kind === 'label' ? 'button' : 'div', attrs, [
      'Errors: 0', ...Array.from({ length: limit }, () => element('span', { 'data-private': '' }, ['IGNORED'])),
      'but failures are still loading',
    ]));
    // A plausible prefix must not become a healthy assertion or a grounded action label.
    expect(value.incomplete).toBe(true);
    expect(JSON.stringify(value)).not.toContain('IGNORED');
  });
  it.each(['result', 'label', 'page'].flatMap(kind => ['single-node', 'later-node'].map(shape => [kind, shape])))('flags character-truncated %s evidence (%s)', (kind, shape) => {
    const attrs = kind === 'result' ? { 'data-sre-result': 'errors' }
      : kind === 'label' ? { 'data-sre-action': 'show-errors', 'data-sre-safe': 'true' } : {};
    const max = kind === 'label' ? 120 : kind === 'result' ? 501 : 8000;
    const prefix = (kind === 'label' ? 'View errors' : 'Errors: 0').padEnd(max, ' ');
    const suffix = 'delete deployment / failures still loading';
    const children = shape === 'single-node' ? [prefix + suffix] : [prefix, suffix];
    expect(observe(element(kind === 'label' ? 'button' : 'div', attrs, children)).incomplete).toBe(true);
    // Exactly the boundary, with no discarded evidence, remains complete.
    expect(observe(element(kind === 'label' ? 'button' : 'div', attrs, [prefix])).incomplete).toBe(false);
  });
  it('allows exactly the text-node budget without an incomplete false positive', () => {
    const value = observe(element('div', { 'data-sre-result': 'errors' }, [
      'Errors: 0', ...Array.from({ length: 4999 }, () => element('span', { 'data-private': '' }, ['IGNORED'])),
    ]));
    expect(value.incomplete).toBe(false);
    expect(value.result).toBe('Errors: 0');
  });
  it('normalizes visible text and retains the oversized-result rejection sentinel', () => {
    expect(observe(element('div', { 'data-sre-result': 'errors' }, ['  Errors:\n 0  '])).result).toBe('Errors: 0');
    expect(observe(element('div', { 'data-sre-result': 'errors' }, ['x'.repeat(600)])).result).toHaveLength(501);
  });
});
