# Live API Latency Benchmark

This repository contains a utility script for benchmarking Gemini Live API
latency when connecting through either the Gemini Developer API or the Vertex AI
Gemini backend.

## Prerequisites

- Python 3.11+
- `pip install google-genai`
- Set the environment variables or credentials required for each backend:
  - **Developer API**: `export GEMINI_API_KEY="..."`.
  - **Vertex AI**: authenticate with `gcloud auth application-default login`
    and ensure the project has access to the selected model (default:
    `sascha-playground-doit` in `us-central1`).

## Usage

```bash
cp .env.example .env  # fill in your credentials
export $(grep -v '^#' .env | xargs)  # or rely on your shell's dotenv loader
python performance/live_api_latency_benchmark.py \
  --iterations 5 \
  --prompt "Respond with the single word hello."
```

Key flags:

- `--backends developer,vertex` to choose which backends run.
- `--input-audio path/to/audio.pcm` to stream audio alongside the text prompt.
- `--output metrics.json` to capture raw metrics for further analysis.
- `--model gemini-2.5-flash-preview-native-audio-dialog` (default) for Gemini
  Developer API sessions.
- `--vertex-model gemini-2.0-flash-live-preview-04-09` (default) to use a Vertex
  Live API model; override this flag to try other Vertex offerings.
- `--vertex-api-version v1` if you need to pin Vertex Live API to a specific
  version (defaults to `v1`, configurable via `VERTEX_API_VERSION`).
- `--artifact-dir artifacts` saves captured audio into per-backend folders (for
  example, `artifacts/developer` and `artifacts/vertex`).
- `--enable-thoughts` re-enables native thinking with a 1024-token budget;
  thinking is disabled by default by setting the budget to `0` in the config.

The script prints per-run metrics (connection, first chunk, total latency) and
averages for each backend so you can compare performance characteristics.

Environment variables are read automatically; you can populate them by copying
`.env.example` to `.env` and updating the values, then running
`export $(grep -v '^#' .env | xargs)` (or use your preferred dotenv loader)
before launching the benchmark.

Add `VERTEX_MODEL` and/or `VERTEX_API_VERSION` to `.env` if you want to change
the Vertex defaults without passing flags on every run.
