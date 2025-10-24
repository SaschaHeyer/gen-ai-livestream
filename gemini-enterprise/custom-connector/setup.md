# Custom Connector Setup Guide

Follow this end-to-end guide to recreate the Gemini Enterprise custom connector demo.

## 0. Prerequisites
- Python **3.10+** (`python3 --version`).
- Google Cloud SDK (`gcloud`) installed and on your PATH.
- Access to project `sascha-playground-doit` with permissions to enable APIs, create service accounts, and manage Discovery Engine.
- Gemini Enterprise identity provider configured (for example Google Workspace). You can verify later using step 9.3.

## 1. Clone & Install Dependencies
```bash
git clone <repo-url>
cd gemini-enterprise/custom-connector
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

## 2. Authenticate with Google Cloud
```bash
gcloud auth login
gcloud config set project sascha-playground-doit
gcloud auth application-default login
gcloud auth application-default set-quota-project sascha-playground-doit
```

## 3. Enable Required APIs
```bash
gcloud services enable \
  discoveryengine.googleapis.com \
  aiplatform.googleapis.com \
  cloudfunctions.googleapis.com \
  run.googleapis.com
```

## 4. Create the Connector Service Account
```bash
gcloud iam service-accounts create agentspace-connector \
  --display-name="Agentspace Connector"

for ROLE in \
  roles/discoveryengine.admin \
  roles/storage.objectViewer \
  roles/iam.serviceAccountTokenCreator; do
  gcloud projects add-iam-policy-binding sascha-playground-doit \
    --member=serviceAccount:agentspace-connector@sascha-playground-doit.iam.gserviceaccount.com \
    --role=$ROLE \
    --condition=None
done
```

## 5. Understand the Demo Content
- Files live under `demo-content/` (handbook, FAQ, runbook).
- `demo-content/catalog.json` holds metadata and `allowedPrincipals` for each document.
- `acl-mapping.yaml` mirrors the intended persona visibility.

## 6. Provision an ACL-Enabled Datastore
The following one-off command uses the Discovery Engine SDK (`google-cloud-discoveryengine`). It pulls in `DataStoreServiceClient` and `DocumentProcessingConfig`, constructs the configuration, and invokes `create_data_store` exactly once to provision the demo datastore.
```bash
python - <<'PY'
from google.cloud import discoveryengine_v1alpha as de

project='sascha-playground-doit'
location='global'
parent=de.DataStoreServiceClient().collection_path(project, location, 'default_collection')

chunk = de.DocumentProcessingConfig.ChunkingConfig(
    layout_based_chunking_config=de.DocumentProcessingConfig.ChunkingConfig.LayoutBasedChunkingConfig(
        chunk_size=400,
        include_ancestor_headings=True,
    )
)
parsing = de.DocumentProcessingConfig.ParsingConfig(
    layout_parsing_config=de.DocumentProcessingConfig.ParsingConfig.LayoutParsingConfig()
)

request = de.CreateDataStoreRequest(
    parent=parent,
    data_store_id='demo_local_docs_acl_v1',
    data_store=de.DataStore(
        display_name='Demo Local Docs ACL',
        industry_vertical=de.IndustryVertical.GENERIC,
        solution_types=[de.SolutionType.SOLUTION_TYPE_SEARCH],
        content_config=de.DataStore.ContentConfig.CONTENT_REQUIRED,
        acl_enabled=True,
        document_processing_config=de.DocumentProcessingConfig(
            chunking_config=chunk,
            default_parsing_config=parsing,
        ),
    ),
)

de.DataStoreServiceClient().create_data_store(request=request).result()
PY
```

## 7. Import Documents with ACLs Active
> Run these commands from the `gemini-enterprise/custom-connector` directory so the `.venv/` path resolves correctly.
```bash
.venv/bin/python tools/import_local_docs.py \
  --project sascha-playground-doit \
  --location global \
  --data-store-id demo_local_docs_acl_v1 \
  --content-root demo-content
```
- Add `--dry-run` to inspect payloads before sending.
- Re-run after any content or ACL updates.

## 8. Optional: Real-Time Watcher for Demos
> Also run from `gemini-enterprise/custom-connector` so the virtualenv is accessible.
```bash
.venv/bin/python tools/watch_local_docs.py \
  --project sascha-playground-doit \
  --location global \
  --data-store-id demo_local_docs_acl_v1 \
  --content-root demo-content \
  --verbose
```
- Leave running in a dedicated terminal; stop with `Ctrl+C`.

## 9. Validation Checklist
1. **Chunked search sanity check** (service-account token may return empty results because of ACLs):
   ```bash
   PROJECT=sascha-playground-doit DATA_STORE_ID=demo_local_docs_acl_v1 ./scripts/smoke_search.sh | jq
   ```
2. **Gemini Enterprise UI:** register the datastore, impersonate `sascha@doit.com` (sees all docs) and `another-user@doit.com` (no runbook) via “View as user”.
3. **Confirm identity provider hook:**
   ```bash
   python - <<'PY'
   from google.cloud import discoveryengine_v1alpha as de
   client = de.AclConfigServiceClient()
   cfg = client.get_acl_config(name=client.acl_config_path('sascha-playground-doit', 'global'))
   print(cfg)
   PY
   ```
   Ensure `idp_type` matches your SSO provider.

## 10. Gemini Enterprise Console Tasks
1. Register `demo_local_docs_acl_v1` as the custom connector.
2. Map personas to groups (or keep direct user ACLs). See `custom-audience.md` for options.
3. Build a dedicated assistant workspace scoped to this datastore.
4. Rehearse workshop queries using persona impersonation.

## 11. Maintenance Tips
- Re-run `tools/import_local_docs.py` whenever content or ACL changes occur.
- Watch import operations with `gcloud discovery-engine operations list --project sascha-playground-doit --location=global`.
- Use `tools/import_local_docs.py --dry-run` before production imports.
- When decommissioning, delete the datastore:
  ```bash
  python - <<'PY'
  from google.cloud import discoveryengine_v1alpha as de
  client = de.DataStoreServiceClient()
  name='projects/sascha-playground-doit/locations/global/collections/default_collection/dataStores/demo_local_docs_acl_v1'
  client.delete_data_store(request={'name': name}).result()
  PY
  ```
