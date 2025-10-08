# Cloud Run Job for Automation

This repository packages the Cloud Run Job that executes `automation-gemini-computer-use.py`.

## Build & deploy

From the repository root, run:

```bash
gcloud builds submit .
```

This uploads the job directory—including the automation script and static assets—so the image contains everything needed at runtime.  
Cloud Build produces `us-central1-docker.pkg.dev/$PROJECT_ID/automation/automation-job:latest` and deploys/updates the Cloud Run Job automatically.  
Adjust `_REGION`, `_REPOSITORY`, `_JOB_NAME`, or `_IMAGE_TAG` inside `cloudbuild.yaml` if you need different settings.

## Execute the job

```bash
gcloud run jobs execute automation-job \
  --region us-central1 \
  --args="--target-url=https://127.0.0.1:8765/index.html"
```

Environment variables (or CLI args) recognised by `job_main.py`:

| Name | Description | Default |
|------|-------------|---------|
| `TARGET_URL` / `--target-url` | URL to automate | Hosted demo URL |
| `NOTE_TEXT` / `--note-text` | Note to insert | “Automated upload triggered by Gemini Computer Use agent.” |
| `PDF_URI` / `--pdf-uri` | Local path or `gs://` URI for the PDF upload | _(required)_ |
| `VERTEXAI_PROJECT` / `GOOGLE_CLOUD_PROJECT` | Vertex AI project override | Auto-detected from runtime |
| `VERTEXAI_LOCATION` / `GOOGLE_CLOUD_REGION` | Vertex AI region | `us-central1` |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Optional fallback API key when Vertex AI auth is unavailable | _(optional)_ |

If you supply a `gs://` URI, ensure the job’s service account has `storage.objects.get` on that bucket. Cloud Run instances are ephemeral, so anything written to `/app/result` should be exported to Cloud Storage or Cloud Logging if you need to keep it.
The job calls Gemini through Vertex AI by default, so grant the service account the `Vertex AI User` role (or equivalent) and allow it to access any dependent resources.
Provide a PDF via `--pdf-uri` or `PDF_URI`; the image no longer includes a bundled sample file.
