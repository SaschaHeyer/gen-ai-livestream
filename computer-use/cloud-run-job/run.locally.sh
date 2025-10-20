export GEMINI_API_KEY="ADD KEY HERE"

PLAYWRIGHT_HEADLESS=false python job_main.py --target-url=https://browser-use-demo-24173060393.us-central1.run.app/ \
      --pdf-uri=/Users/sascha/Desktop/development/gen-ai-livestream/computer-use/cloud-run-job/sample.pdf \
      --note-text="test"
