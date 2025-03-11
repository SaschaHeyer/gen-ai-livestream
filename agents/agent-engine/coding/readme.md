# GitHub Agent


## Ideas

### Add Code Execution to test if fix is successfully passing all tests
https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/code-execution#googlegenaisdk_tools_code_exec_with_txt-python_genai_sdk


gcloud beta run services logs read github-webhook


## Webhook Usage

The webhook service handles GitHub webhook events to analyze issues and maintain code embeddings:

1. **Setup**:
   - Deploy the webhook using Cloud Build and Cloud Run:
     ```
     cd webhook
     gcloud builds submit --config cloudbuild.yaml
     ```
   - Configure your GitHub repository to send webhook events to the deployed endpoint: `https://github-webhook-[hash].run.app/webhook`
   - Set webhook to trigger on "Issues" and "Push" events

2. **Features**:
   - **Issue Analysis**: When a new GitHub issue is opened, the webhook calls a Vertex AI Reasoning Engine to analyze and respond to the issue
   - **Code Embeddings**: When code is pushed to the repository, the webhook:
     - Fetches the content of changed files
     - Generates embeddings using Vertex AI
     - Stores embeddings in Firestore for code search/retrieval
     - Removes embeddings for deleted files

3. **Viewing Logs**:
   ```
   gcloud beta run services logs read github-webhook
   gcloud beta run services logs tail github-webhook
   ```

## Embedding

The embeddings stored in firebase require a index

```
gcloud firestore indexes composite create \
--collection-group=code-embeddings \
--query-scope=COLLECTION \
--field-config field-path=embedding,vector-config='{"dimension":"256", "flat": {}}' \
--database="(default)"
```
