#!/usr/bin/env node
// ternlight-search — point on-device semantic search at YOUR own list of strings.
//
// Usage:
//   node ternlight-search.mjs <corpus.json> "<query>" [--topK 3]
//
// corpus.json is a JSON array of strings, or an array of { text, ... } objects.
// Embeds the corpus once, embeds the query, prints the top-K by cosine similarity.
// Pure local WASM inference, no API key, no network.
import { readFileSync } from 'node:fs';
import { embed, cosineSim, engineInfo } from '@ternlight/base';

const args = process.argv.slice(2);
if (args.length < 2) {
  console.error('usage: node ternlight-search.mjs <corpus.json> "<query>" [--topK N]');
  process.exit(1);
}
const [corpusPath, query] = args;
const topKFlag = args.indexOf('--topK');
const topK = topKFlag !== -1 ? Number(args[topKFlag + 1]) : 3;

const raw = JSON.parse(readFileSync(corpusPath, 'utf8'));
// accept ["str", ...] or [{text:"str"}, ...]
const docs = raw.map((d) => (typeof d === 'string' ? d : d.text));

console.error(engineInfo());
const t0 = performance.now();
const index = docs.map((text) => ({ text, v: embed(text) }));
console.error(`indexed ${docs.length} docs in ${(performance.now() - t0).toFixed(1)} ms\n`);

const qv = embed(query);
const hits = index
  .map(({ text, v }) => ({ text, sim: cosineSim(qv, v) }))
  .sort((a, b) => b.sim - a.sim)
  .slice(0, topK);

console.log(`query: ${query}\n`);
for (const h of hits) console.log(`${h.sim.toFixed(3)}  ${h.text}`);
