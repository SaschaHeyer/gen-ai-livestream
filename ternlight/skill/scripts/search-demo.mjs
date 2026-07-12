// Beat 2 — turn embed into a real search. Index a small help corpus once, then query it.
// Run: node 02-search.mjs
import { embed, cosineSim } from '@ternlight/base';

// A tiny creator help center for the show. In a real app these come from your CMS.
const docs = [
  'Going live: press the Go Live button to start broadcasting your stream',
  'Scheduling posts: queue a post and it publishes automatically at the time you set',
  'Time zones: streams default to Europe Berlin, change it under settings',
  'Refunds: how to request a refund on a paid membership',
  'Overlays: add a lower third or a standby screen to your scene',
  'Chat moderation: ban, timeout, or slow mode your live chat',
  'Uploading a thumbnail: replace the auto thumbnail with your own image',
  'Billing: update the card on file for your subscription',
  'Multistream: send one broadcast to YouTube and LinkedIn at the same time',
  'Clips: cut a short highlight from a past broadcast to share',
];

// Index once. This is the upfront cost, embed every doc a single time.
const t0 = performance.now();
const index = docs.map((text) => ({ text, v: embed(text) }));
const indexMs = performance.now() - t0;
console.log(`indexed ${docs.length} docs in ${indexMs.toFixed(1)} ms\n`);

function search(query, topK = 3) {
  const q = embed(query);
  return index
    .map(({ text, v }) => ({ text, sim: cosineSim(q, v) }))
    .sort((a, b) => b.sim - a.sim)
    .slice(0, topK);
}

for (const query of [
  'how do I start streaming',
  'schedule my content ahead of time',
  'what time zone are broadcasts in',
  'send my stream to two platforms at once',
]) {
  const t = performance.now();
  const hits = search(query);
  const ms = performance.now() - t;
  console.log(`Q: ${query}   (${ms.toFixed(1)} ms)`);
  for (const h of hits) console.log(`   ${h.sim.toFixed(3)}  ${h.text}`);
  console.log();
}
