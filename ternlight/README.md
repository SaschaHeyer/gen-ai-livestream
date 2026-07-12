# Ternlight, semantic search in the browser with a 7 MB WASM model

Gen AI Livestream e06. On-device semantic embeddings for JavaScript, the whole model plus tokenizer plus engine in one WebAssembly file. Call `embed(text)`, get a 384-dim vector on the CPU, synchronously, no API key and no runtime download.

Try it live, no install, everything runs in your browser: https://ternlight-demo-1051190601763.us-central1.run.app

Everything runnable lives under [`skill/`](skill/), one folder, one source of truth.

- [skill/SKILL.md](skill/SKILL.md) — the skill, current facts, quick start, gotchas, and the decision guidance.
- [skill/scripts/ternlight-search.mjs](skill/scripts/ternlight-search.mjs) — point on-device search at your own JSON corpus.
- [skill/scripts/three-lines.mjs](skill/scripts/three-lines.mjs) and [search-demo.mjs](skill/scripts/search-demo.mjs) — the episode demos, verified.
- [skill/web/](skill/web/) — the in-browser demo, a search box wired to the wasm.

## Run it

```bash
cd skill/scripts && npm install
node ternlight-search.mjs your-corpus.json "your query" --topK 3

cd ../web && npm install && npm run dev
```

## Deploy the demo

The browser demo is a static site, it deploys to Cloud Run as an nginx container that serves the built `dist/`. The `Dockerfile` and `nginx.conf` in `skill/web/` set the `application/wasm` MIME and gzip the engine.

```bash
gcloud run deploy ternlight-demo --source skill/web --region us-central1 --allow-unauthenticated
```

Ternlight is an open source project by [Paradane](https://www.linkedin.com/company/paradane). Package on npm, [@ternlight/base](https://www.npmjs.com/package/@ternlight/base).
