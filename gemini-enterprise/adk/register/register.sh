#!/usr/bin/env bash
# Simplicity-first wrapper: always call register_agent.py with the same args.

set -euo pipefail

python "$(dirname "$0")/register_agent.py" \
  --project-id "sascha-playground-doit" \
  --app-id "gemini-enterprise" \
  --display-name "Help Desk Coordinator" \
  --description "Routes billing vs. support inquiries." \
  --reasoning-engine-location "us-central1" \
  --adk-deployment-id "1546718191164588032" \
  --location "global" \
  --endpoint "global" \
  --icon-uri "https://storage.googleapis.com/doit-sascha-public/gemini-enterprise/logo.png" \
  "$@"
