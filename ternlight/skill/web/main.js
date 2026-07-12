import { embed, cosineSim, engineInfo } from '@ternlight/base';

// Same creator help corpus as the Node demo. In a real app these come from your CMS.
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

document.getElementById('engine').textContent = engineInfo();

// Index once at load. Every search after this is pure local math, no network.
const t0 = performance.now();
const index = docs.map((text) => ({ text, v: embed(text) }));
const indexMs = (performance.now() - t0).toFixed(0);

const q = document.getElementById('q');
const stat = document.getElementById('stat');
const results = document.getElementById('results');
stat.textContent = `indexed ${docs.length} docs in ${indexMs} ms — now type, every keystroke searches locally`;

function render(query) {
  if (!query.trim()) { results.innerHTML = ''; return; }
  const t = performance.now();
  const qv = embed(query);
  const hits = index
    .map(({ text, v }) => ({ text, sim: cosineSim(qv, v) }))
    .sort((a, b) => b.sim - a.sim)
    .slice(0, 3);
  const ms = (performance.now() - t).toFixed(1);
  stat.textContent = `searched ${docs.length} docs in ${ms} ms, no network request`;
  results.innerHTML = hits
    .map((h) => `<div class="hit"><span class="sim">${h.sim.toFixed(3)}</span><span>${h.text}</span></div>`)
    .join('');
}

q.addEventListener('input', (e) => render(e.target.value));
// expose for automated verification
window.__ternSearch = render;
