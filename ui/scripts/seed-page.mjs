#!/usr/bin/env node
// Node 22.18+ type stripping runs the editor's actual validator; no second schema/parser.
import { writeFileSync } from 'node:fs';
import { parseArgs } from 'node:util';
import { createSeed, portable, serialize } from '../src/workflow.ts';

const usage = 'npm run seed -- open "https://example.com/search?query={xyz}" --output page.json';
try {
  const { values, positionals } = parseArgs({
    options: { output: { type: 'string' }, help: { type: 'boolean' } },
    allowPositionals: true,
  });
  if (values.help) {
    console.log(usage);
  } else {
    if (positionals.length !== 2 || positionals[0] !== 'open' || !values.output) throw new Error('Invalid arguments');
    const manifest = serialize(portable(createSeed(positionals[1]))) + '\n';
    // Exclusive creation preserves existing drafts. Validation finishes before opening any file.
    writeFileSync(values.output, manifest, { encoding: 'utf8', flag: 'wx', mode: 0o600 });
    console.log('Created offline page manifest. No browser or model was invoked.');
  }
} catch {
  // Never echo URLs, query values, output paths or unknown arguments into logs.
  console.error('Cannot create seed: check arguments, URL safety, and that the output is a new writable file.');
  console.error(usage);
  process.exitCode = 2;
}
