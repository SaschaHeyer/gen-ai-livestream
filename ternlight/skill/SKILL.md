---
name: ternlight
description: Use this skill when adding on-device semantic search, FAQ matching, deduplication, clustering, or RAG reranking to a JavaScript or TypeScript app with no server, no API key, and no runtime model download. Covers the @ternlight/base and @ternlight/mini WASM sentence-embedding packages, the embed / cosineSim / similar API, indexing a corpus once and searching it, and the Vite and webpack bundler setup for the browser build. Works in Node, browsers, Cloudflare Workers, Vercel Edge, Deno, and Bun.
---

# Ternlight On-Device Embeddings Skill

Ternlight ships a sentence-embedding model, its tokenizer, and a from-scratch Rust inference engine inside a single WebAssembly file. You call `embed(text)` and get a 384-dim unit vector back on the CPU, synchronously, with no network call and no model download at runtime. Use it for semantic search over small-to-medium corpora, FAQ matching, dedup, and RAG reranking.

> [!IMPORTANT]
> Install one of two packages, same API, different size and quality tier.
> `npm install @ternlight/base` is the quality tier, ~7 MB gzipped on the wire, ~5 ms per embed.
> `npm install @ternlight/mini` is the small tier, ~5.5 MB, under 2 ms, slightly lower quality.
> `embed()` is SYNCHRONOUS in Node and in bundled browser builds. There is no init call and no await. The model already lives inside the wasm. Latest published version is 0.1.0, MIT licensed.

> [!IMPORTANT]
> `embed(text)` returns a `Float32Array` of length 384, L2-normalized. Because vectors are unit-length, `cosineSim(a, b)` is a plain dot product. Input is tokenized with BERT WordPiece and truncated at 128 tokens, roughly 95 English words. Longer text is silently cut, so chunk your documents small.

> [!WARNING]
> In-browser embeddings are not new. transformers.js has run embedding models in the browser for years. What Ternlight adds is the packaging, a BitNet-style ternary model (weights are -1, 0, +1) small enough to bake the whole model plus tokenizer plus engine into one 7 MB wasm and call it synchronously with no runtime download. Do not claim a first-ever in-browser embedding capability, claim the size and the zero-download story.

> [!WARNING]
> The repo `docs/architecture.md` lists the model as d_model 256, 4 heads, ffn 1024, ~9.5M params. The shipped v0.1.0 engine does NOT match that. Ask the engine itself with `engineInfo()`, which reports `tern-engine v1 | embedding_format=int4 | vocab=30522 d_model=384 n_layers=2 n_heads=6 ffn_dim=1536 output_dim=384 max_seq_len=128`. When the doc and the binary disagree, trust the binary.

---

## Quick Start

Node, three lines, no async anywhere.

```js
import { embed, cosineSim, similar } from '@ternlight/base';

// two ways of asking the same thing sit close together
cosineSim(embed('reset my password'), embed('I forgot my password')); // 0.884

// top-K semantic search over any list of strings
similar('how do I reset my password', [
  'Resetting a forgotten password',
  'Update your billing address',
  'Track the status of your delivery',
], { topK: 2 });
// [{ text: 'Resetting a forgotten password', sim: ... }, ...]
```

For repeated searches over the same corpus, embed it ONCE up front and reuse the vectors. This is the pattern you want in any real app.

```js
import { embed, cosineSim } from '@ternlight/base';

const docs = [ /* your strings */ ];
const index = docs.map((text) => ({ text, v: embed(text) })); // one-time cost

function search(query, topK = 3) {
  const q = embed(query);
  return index
    .map(({ text, v }) => ({ text, sim: cosineSim(q, v) }))
    .sort((a, b) => b.sim - a.sim)
    .slice(0, topK);
}
```

> [!WARNING]
> The very first `embed()` call in a process pays a one-time wasm warmup of roughly 200 ms. After that, each embed is a few milliseconds. Measured on an M-series CPU, indexing 10 short docs in a warm process took about 8 ms total, and each query embed was 2.5 to 5 ms. Do the corpus indexing once at startup, never per request.

### Browser with Vite

The browser build imports the wasm as an ES module asset, so Vite needs the wasm plugin. That is the entire setup.

```js
// vite.config.js
import wasm from 'vite-plugin-wasm';
export default { plugins: [wasm()] };
```

```js
// main.js — same embed/cosineSim/similar API as Node
import { embed, cosineSim, engineInfo } from '@ternlight/base';
```

> [!WARNING]
> Do not add `vite-plugin-top-level-await` on Vite 8. It pulls a `rollup` peer that the rolldown-based Vite 8 does not expose, and the build dies with `Cannot find module 'rollup'`. The wasm plugin alone is enough on modern targets. On webpack 5 the equivalent is `experiments: { asyncWebAssembly: true }`. Node needs no config at all.

> [!IMPORTANT]
> Every search runs fully client-side. Verified in a real browser, after loading the page and running five searches, the total resource count stayed at exactly two, the JS glue and the one-time wasm fetch. No query fires a network request. The user's search text never leaves the tab.

## When to use it, and when not

Measured behavior and honest limits, all confirmed on real runs.

- **Corpus size.** This is a small-to-medium tool, hundreds to low thousands of chunks, embed once and brute-force cosine. For hundreds of thousands of documents, reach for a real vector database instead.
- **Quality.** The authors report 0.844 Spearman versus all-MiniLM-L6-v2 for base, 0.835 for mini, and 0.465 SciFact NDCG@10. In practice, the README examples reproduce exactly, `reset my password` versus `I forgot my password` scores 0.884. Idiomatic paraphrases with zero shared words score lower, `how do I go live on the stream` versus `start broadcasting my show` was only 0.403. Ranking still works because relative order is what matters, but keep the similarity score visible so a weak match reads honestly.
- **Token cap.** 128 tokens, silently truncated. Chunk before you embed.
- **Indexing cost is real on big corpora.** A large corpus embedded on page load will pin the CPU for a noticeable moment. Pre-compute the vectors and cache them, do not re-index on every visit.

## Workflow

When the request is to search a user's own data, use the parameterized script rather than hand-writing a loop.

1. Put the corpus in a JSON file, an array of strings or of `{ text }` objects.
2. Run `node scripts/ternlight-search.mjs <corpus.json> "<query>" [--topK N]`.
3. Report the ranked matches and their scores back.

```bash
node scripts/ternlight-search.mjs kb.json "how do I catch an error" --topK 3
# 0.577  Handle exceptions with try and except blocks
# ...
```

## Dependencies and Prerequisites

- Node >= 18. `npm install @ternlight/base` (or `@ternlight/mini`).
- Browser build additionally needs `vite-plugin-wasm` on Vite, or `experiments: { asyncWebAssembly: true }` on webpack 5.
- No API key, no service account, no GPU, nothing to authenticate.

## Supporting files

- [scripts/ternlight-search.mjs](scripts/ternlight-search.mjs) — the parameterized utility, point it at your own JSON corpus. `node scripts/ternlight-search.mjs corpus.json "your query" --topK 3`
- [scripts/three-lines.mjs](scripts/three-lines.mjs) — frozen episode reproduction, the embed and cosineSim intro. `node scripts/three-lines.mjs`
- [scripts/search-demo.mjs](scripts/search-demo.mjs) — frozen episode reproduction, index a small corpus and run a few queries. `node scripts/search-demo.mjs`
- [web/](web/) — the in-browser demo, a search box wired to the wasm. `cd web && npm install && npm run dev`

## Documentation Pages

You MUST fetch the matching page below before writing code against this package. These are the source of truth for the API shape, the quality numbers, and the bundler setup, do not rely solely on the examples above.

- https://github.com/soycaporal/ternlight
- https://www.npmjs.com/package/@ternlight/base
- https://github.com/soycaporal/ternlight/blob/main/docs/architecture.md

Ternlight is an open source project by Paradane, https://www.linkedin.com/company/paradane.

## From the episode

Gen AI Livestream e06, semantic search in the browser with a 7 MB WASM model. Video link to follow.
