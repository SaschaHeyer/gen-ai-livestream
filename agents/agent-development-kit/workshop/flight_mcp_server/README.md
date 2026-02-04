# Flight MCP Server

A sample MCP server for flight booking, capable of searching, retrieving details, and booking flights.

## 🚀 Deploy to Cloud Run

Deploy this server to Google Cloud Run with a single command:

```bash
gcloud run deploy flight-mcp-server \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

This will build the container using the provided `Dockerfile` and deploy it.

## 🛠️ Local Development

**1. Install dependencies:**
```bash
uv sync
```

**2. Run the server:**
```bash
uv run server.py
```

**3. Test the tools:**
Open a new terminal and run:
```bash
uv run test_server.py
```
