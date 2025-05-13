# Deploying ADK Audio Assistant to Google Cloud Run

This guide walks through deploying the ADK Audio Assistant to Google Cloud Run with session affinity enabled for persistent WebSocket connections.

## Prerequisites

1. Google Cloud SDK installed and configured
2. Docker installed
3. Access to Google Cloud project with permissions to deploy Cloud Run services
4. Enabled Cloud Run, Artifact Registry, and Cloud Build APIs

## Deployment Steps

### 1. Authenticate with Google Cloud

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 2. Build and Deploy Manually

You can build and deploy manually using:

```bash
# Navigate to the server directory
cd /path/to/server

# Create Artifact Registry repository if it doesn't exist
gcloud artifacts repositories create adk-audio-assistant \
  --repository-format=docker \
  --location=us-central1 \
  --description="Repository for ADK Audio Assistant"

# Configure Docker to use Google Cloud as a credential helper
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build the Docker image
docker build -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/adk-audio-assistant/audio-assistant:latest .

# Push the image to Artifact Registry
docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/adk-audio-assistant/audio-assistant:latest

# Deploy to Cloud Run with session affinity enabled
gcloud run deploy adk-audio-assistant \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/adk-audio-assistant/audio-assistant:latest \
  --region us-central1 \
  --platform managed \
  --port 8765 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --session-affinity \
  --set-annotations=run.googleapis.com/websocket=true
```

### 3. Deploy Using Cloud Build

Alternatively, deploy using Cloud Build with the included cloudbuild.yaml file:

```bash
# Navigate to the server directory
cd /path/to/server

# Submit build
gcloud builds submit --config cloudbuild.yaml .
```

## Cloud Service Account Permissions

If you encounter permission errors with the Cloud Build service account, grant it the necessary permissions:

```bash
# Get the service account email - usually in the format: 
# YOUR_PROJECT_NUMBER@cloudbuild.gserviceaccount.com
gcloud projects get-iam-policy YOUR_PROJECT_ID --format='table(bindings.role,bindings.members)' | grep cloudbuild

# Grant needed permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=serviceAccount:YOUR_SERVICE_ACCOUNT_EMAIL \
  --role=roles/pubsub.publisher

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=serviceAccount:YOUR_SERVICE_ACCOUNT_EMAIL \
  --role=roles/source.reader

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=serviceAccount:YOUR_SERVICE_ACCOUNT_EMAIL \
  --role=roles/logging.logWriter
```

## Important Configuration Notes

### Port Configuration

The `--port=8765` flag specifies the port inside the container where the application listens. This is important because our WebSocket server listens on port 8765 instead of the default 8080 that Cloud Run typically expects.

### WebSocket Support

The `--set-annotations=run.googleapis.com/websocket=true` annotation is critical for WebSocket connectivity. This enables WebSocket protocol support in Cloud Run.

### Session Affinity

The `--session-affinity` flag ensures that requests from the same client are routed to the same service instance. This is important for maintaining WebSocket connections and session state.

Key behaviors with session affinity:
- Client requests are directed to the same instance when possible
- Instances can still serve multiple different clients
- If an instance is terminated, session affinity is broken
- Session affinity uses a cookie with a 30-day TTL

### Updating the Client

After deployment, update the WebSocket URL in the client application to point to your Cloud Run service URL:

```javascript
// In client/audio-client.js, change:
const audioClient = new AudioClient('wss://YOUR-CLOUD-RUN-SERVICE-URL');
```

Note: Cloud Run services use HTTPS, so the WebSocket URL should use the secure `wss://` protocol.

## Monitoring and Troubleshooting

- View logs in the Google Cloud Console under Cloud Run > adk-audio-assistant > Logs
- Monitor instance count and metrics under Cloud Run > adk-audio-assistant > Metrics
- Check Cloud Run service details to verify session affinity is enabled