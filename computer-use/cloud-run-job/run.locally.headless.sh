USE_VERTEXAI=0 \
  GEMINI_API_KEY="ADD KEY HERE" \
  TELEMETRY_PROJECT=gen-ai-livestream \
  TELEMETRY_GCS_BUCKET=gen-ai-livestream \
  PLAYWRIGHT_HEADLESS=false \
  CASE_ID=12345 \
  python job_main.py \
    --target-url=https://browser-use-demo-24173060393.us-central1.run.app/ \
    --pdf-uri=/Users/sascha/Desktop/development/gen-ai-livestream/computer-use/cloud-run-job/sample.pdf
