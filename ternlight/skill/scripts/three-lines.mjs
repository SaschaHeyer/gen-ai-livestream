// Beat 1 — the three lines. embed, cosineSim, no async init.
// Run: node 01-three-lines.mjs
import { embed, cosineSim, engineInfo } from '@ternlight/base';

console.log('engine:', engineInfo());

// text -> 384-dim L2-normalized Float32Array, synchronous, no await anywhere
const v = embed('how do I go live on the stream');
console.log('embed() ->', v.constructor.name, 'length', v.length);

// two ways of saying the same creator task should sit close together
console.log(
  'go live vs start broadcasting :',
  cosineSim(embed('how do I go live on the stream'), embed('start broadcasting my show')).toFixed(3),
);
console.log(
  'schedule vs queue for tomorrow:',
  cosineSim(embed('schedule this post for later'), embed('queue it to publish tomorrow')).toFixed(3),
);

// an unrelated pair should sit far apart, that contrast is the whole point
console.log(
  'go live vs refund policy     :',
  cosineSim(embed('how do I go live on the stream'), embed('what is your refund policy')).toFixed(3),
);
