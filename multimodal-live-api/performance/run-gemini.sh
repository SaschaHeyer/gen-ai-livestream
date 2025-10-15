#!/bin/bash

# Simple helper to benchmark the Gemini Developer API backend with a fixed prompt.
# Requires no external environment variables because the API key is embedded below.

export GEMINI_API_KEY="..."

python3 live_api_latency_benchmark.py \
    --backends developer \
    --iterations 5 \
    --prompt "Respond with the single word hello." \
    --model gemini-2.5-flash-native-audio-preview-09-2025
