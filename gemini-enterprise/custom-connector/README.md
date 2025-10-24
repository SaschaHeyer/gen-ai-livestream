# Gemini Enterprise Custom Connector Demo

A fully scripted example of building a Gemini Enterprise (Agentspace) custom connector that ingests local files, enforces fine-grained ACLs, and supports live updates.

---
## Table of Contents
- [Gemini Enterprise Custom Connector Demo](#gemini-enterprise-custom-connector-demo)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Architecture](#architecture)
  - [Prerequisites](#prerequisites)
  - [Setup Guide](#setup-guide)
    - [Clone \& Install](#clone--install)
    - [Authenticate with Google Cloud](#authenticate-with-google-cloud)
    - [Enable Required APIs](#enable-required-apis)
    - [Create Connector Service Account](#create-connector-service-account)
    - [Provision ACL Datastore](#provision-acl-datastore)
    - [Import Documents](#import-documents)
    - [Optional Real-Time Watcher](#optional-real-time-watcher)
    - [Validation Checklist](#validation-checklist)
    - [Gemini Enterprise Console Tasks](#gemini-enterprise-console-tasks)
    - [Maintenance \& Cleanup](#maintenance--cleanup)
  - [Custom Audience Strategies](#custom-audience-strategies)
    - [1. Direct User ACLs (already in place)](#1-direct-user-acls-already-in-place)
    - [2. Google Workspace Groups](#2-google-workspace-groups)
    - [3. Identity Mapping Store (external identities)](#3-identity-mapping-store-external-identities)
  - [Key Files](#key-files)
  - [Extensibility Notes](#extensibility-notes)

---
## Overview
- **Goal:** Demonstrate how to push local Markdown/CSV/TXT files into a Discovery Engine datastore, secure them with ACLs tied to your identity provider, and surface the content inside Gemini Enterprise.
- **Project ID:** `sascha-playground-doit`
- **Personas:** `sascha@domain.com` (full access) and `another-user@domain.com` (FAQ-only).
- **Core scripts:**
  - `tools/import_local_docs.py` – batch ingestion
  - `tools/watch_local_docs.py` – optional live updates
  - `scripts/smoke_search.sh` – chunked search sanity check

---
## Architecture

```
┌────────────────────┐        ┌──────────────────────────┐        ┌────────────────────────┐
│ Local Filesystem   │        │ Discovery Engine (GCP)   │        │ Gemini Enterprise      │
│ - demo-content/    │  push  │ - DataStore (ACL on)     │  serve │ - Knowledge Assist     │
│ - catalog.json     │ ───▶   │ - DocumentService API    │ ───▶   │ - "View as user" UI    │
└────────┬───────────┘        └────────────┬─────────────┘        └────────┬──────────────┘
         │                                   ▲                                  │
         │                                   │                                  │
         │                 identity-aware    │                                  │
         ▼                                   │                                  ▼
┌────────────────────┐        ┌──────────────┴─────────────┐        ┌────────────────────────┐
│ import_local_docs  │──────▶ │ Identity Provider (Google  │ ◀──────│ End Users              │
│ (batch ingestion)  │  API   │ Workspace / Fed ID)        │  auth  │ (sascha@…, another-user@…)  │
└────────┬───────────┘ calls  └────────────────────────────┘        └────────────────────────┘
         │
         ▼
┌────────────────────┐
│ watch_local_docs   │
│ (optional live     │
│  updates)          │
└────────────────────┘
```

- **Local content**: Markdown/CSV/TXT files plus `catalog.json` describing metadata and ACLs.
- **import_local_docs.py**: Reads the catalog, builds `Document` payloads, calls `DocumentServiceClient.import_documents`.
- **watch_local_docs.py**: Monitors the content folder (via `watchfiles`) and upserts changed docs.
- **Discovery Engine datastore**: Provisioned with layout-based chunking and ACL enforcement tied to your identity provider.
- **Gemini Enterprise UI**: Serves user queries, filtering results based on ACLs (“View as user” mirrors the enforcement).

---
## Prerequisites
- Python **3.10+**
- Google Cloud SDK installed
- IAM rights in your GCP project
- Gemini Enterprise identity provider configured

---
## Setup Guide

### Clone & Install
```bash
git clone <repo-url>
cd gemini-enterprise/custom-connector
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

### Authenticate with Google Cloud
```bash
gcloud auth login
gcloud config set project sascha-playground-doit
gcloud auth application-default login
gcloud auth application-default set-quota-project sascha-playground-doit
```

### Enable Required APIs
```bash
gcloud services enable \
  discoveryengine.googleapis.com \
  aiplatform.googleapis.com \
  cloudfunctions.googleapis.com \
  run.googleapis.com
```

### Create Connector Service Account
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

### Provision ACL Datastore
This one-off snippet imports `DataStoreServiceClient` from `google.cloud.discoveryengine_v1alpha`, sets layout-based chunking, and enables ACL enforcement.
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

### Import Documents
> Run from `gemini-enterprise/custom-connector` so `.venv/` is on the path.
```bash
.venv/bin/python tools/import_local_docs.py \
  --project sascha-playground-doit \
  --location global \
  --data-store-id demo_local_docs_acl_v1 \
  --content-root demo-content
```
Add `--dry-run` to inspect the payload before importing.

### Optional Real-Time Watcher
```bash
.venv/bin/python tools/watch_local_docs.py \
  --project sascha-playground-doit \
  --location global \
  --data-store-id demo_local_docs_acl_v1 \
  --content-root demo-content \
  --verbose
```
Leave it running; stop with `Ctrl+C`.

### Validation Checklist
1. **Chunked search sanity check** (ACL stores may return zero results for service-account tokens):
   ```bash
   PROJECT=sascha-playground-doit DATA_STORE_ID=demo_local_docs_acl_v1 ./scripts/smoke_search.sh | jq
   ```
2. **Gemini Enterprise UI**: register the datastore, impersonate each persona (`sascha@domain.com` should see all docs, `another-user@domain.com` should miss the runbook).
3. **Verify IDP hook (optional)**:
   ```bash
   python - <<'PY'
   from google.cloud import discoveryengine_v1alpha as de
   client = de.AclConfigServiceClient()
   cfg = client.get_acl_config(name=client.acl_config_path('sascha-playground-doit', 'global'))
   print(cfg)
   PY
   ```

### Gemini Enterprise Console Tasks
1. Register `demo_local_docs_acl_v1` as a custom connector.
2. Map personas to groups (or keep direct ACLs). See [Custom Audience Strategies](#custom-audience-strategies).
3. Configure an assistant workspace scoped to this datastore.
4. Rehearse workshop queries using “View as user”.

### Maintenance & Cleanup
- Re-run `tools/import_local_docs.py` whenever content or ACLs change.
- Monitor imports: `gcloud discovery-engine operations list --project sascha-playground-doit --location=global`.
- Tear down datastore when done:
  ```bash
  python - <<'PY'
  from google.cloud import discoveryengine_v1alpha as de
  client = de.DataStoreServiceClient()
  name='projects/sascha-playground-doit/locations/global/collections/default_collection/dataStores/demo_local_docs_acl_v1'
  client.delete_data_store(request={'name': name}).result()
  PY
  ```

---
## Custom Audience Strategies
Choose the pattern that matches your audience management needs.

### 1. Direct User ACLs (already in place)
- Use `allowedPrincipals: ["user:sascha@domain.com", ...]` in `catalog.json`.
- Easiest for small demos—no extra setup.

### 2. Google Workspace Groups
1. Create groups (e.g., `launch-ops-demo@domain.com`, `faq-readers-demo@domain.com`).
2. Add the relevant users to each group.
3. Update `catalog.json` with `group:<group-email>` principals.
4. Re-run the import script.

### 3. Identity Mapping Store (external identities)
1. Create the store:
   ```bash
   python - <<'PY'
   from google.cloud import discoveryengine_v1alpha as de
   client = de.IdentityMappingStoreServiceClient()
   parent = client.common_location_path('sascha-playground-doit', 'global')
   store = client.create_identity_mapping_store(parent=parent, identity_mapping_store_id='custom-demo-ims')
   print(store.name)
   PY
   ```
2. Import mappings:
   ```bash
   python - <<'PY'
   from google.cloud import discoveryengine_v1alpha as de
   client = de.IdentityMappingStoreServiceClient()
   ims_name='projects/sascha-playground-doit/locations/global/identityMappingStores/custom-demo-ims'
   entries=[
       de.IdentityMappingEntry(external_identity='launch_ops_group', user_id='sascha@domain.com'),
       de.IdentityMappingEntry(external_identity='faq_group', user_id='another-user@domain.com'),
   ]
   request = de.ImportIdentityMappingsRequest(
       identity_mapping_store=ims_name,
       inline_source=de.ImportIdentityMappingsRequest.InlineSource(identity_mapping_entries=entries),
   )
   client.import_identity_mappings(request=request).result()
   PY
   ```
3. Reference `group:external_group:<identity>` in `catalog.json`, then import.
4. When creating the datastore, set `identity_mapping_store` to the store name.

---
## Key Files
- `demo-content/` – sample knowledge base
- `demo-content/catalog.json` – metadata + ACL assignments
- `acl-mapping.yaml` – human-readable ACL intent
- `tools/import_local_docs.py` – batch ingestion logic
- `tools/watch_local_docs.py` – optional real-time updates
- `scripts/smoke_search.sh` – chunked-search smoke test

---
## Extensibility Notes
- Swap in different data sources by adapting the transformer logic in `import_local_docs.py` (e.g., convert Confluence exports).
- Package ingestion as a Cloud Run Job for scheduled syncs.
- Expand persona management using groups or identity mapping as your user base grows.
- Extend with additional metadata (owners, tags) to power richer Gemini Enterprise experiences.

---
## Discovery Questionnaire
Use this checklist when scoping a new custom connector with a customer:

- Define the use case: which knowledge sources, personas, and access controls are required?
- Plan data sync: how will data be extracted and refreshed (batch exports, source APIs, webhooks)?
- Gather sample content and metadata; decide how ACLs will be represented (users, groups, external identities).
- Provision a Discovery Engine datastore with chunking and ACL enforcement tied to the identity provider.
- Transform source content into Discovery Engine `Document` payloads (content, structData, aclInfo).
- Import documents via the DocumentService API; establish an ongoing sync mechanism (watcher, job, pipeline).
- Register the datastore as a custom connector inside Gemini Enterprise and scope an assistant workspace to it.
- Validate end-to-end by impersonating personas, confirming permissions, and iterating on metadata/ACL mappings.

---
Happy indexing! 🎉
