# Custom Connector Architecture

This document explains how the demo components cooperate to ingest local content into Gemini Enterprise, enforce ACLs, and support real-time updates.

## High-Level View

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
│ (batch ingestion)  │  API   │ Workspace / Fed ID)        │  auth  │ (sascha@…, philipp@…)  │
└────────┬───────────┘ calls  └────────────────────────────┘        └────────────────────────┘
         │
         ▼
┌────────────────────┐
│ watch_local_docs   │
│ (optional live     │
│  updates)          │
└────────────────────┘
```

- **Local Filesystem** – Markdown/CSV/TXT assets plus `catalog.json` describing metadata and `allowedPrincipals`.
- **import_local_docs.py** – Reads the catalog, builds Discovery Engine `Document` payloads, and calls the DocumentService API.
- **watch_local_docs.py** – Listens for file changes and upserts the affected documents (same API client) so demos show near-real-time updates.
- **Discovery Engine Datastore** – Stores documents with chunking enabled and enforces ACLs via the configured identity provider.
- **Identity Provider** – Google Workspace (or federated IDP) resolves which users/groups the ACL principals map to.
- **Gemini Enterprise UI** – Queries the datastore and filters results according to the user identity (“View as user” mirrors the same ACL enforcement).

## Component Detail

### Python Tooling
- `tools/import_local_docs.py`
  - Reads `demo-content/`
  - Builds `Document` objects (content + structData + aclInfo)
  - Calls `DocumentServiceClient.import_documents`
- `tools/watch_local_docs.py`
  - Uses `watchfiles` to detect changes
  - Rebuilds document payloads on modification
  - Calls the same import API for targeted upserts

### Datastore Configuration
- Created manually by running the snippet in `setup.md` (step 6). That snippet imports `DataStoreServiceClient` from `google.cloud.discoveryengine_v1alpha` and calls `create_data_store` once to provision the demo datastore.
- Key settings baked into that command:
  - `content_config = CONTENT_REQUIRED`
  - `acl_enabled = True` (enables document-level ACL enforcement)
  - `document_processing_config` with layout-based chunking (`chunk_size = 400`, `include_ancestor_headings = True`)

### APIs Involved
- **DocumentService API** (`import_documents`, `documents:import` endpoint) – imports content
- **DataStoreService API** (`create_data_store`, `update_document_processing_config`) – provisioning and configuration
- **AclConfigService API** (`get_acl_config`) – verify identity provider linkage

### Identity & ACLs
- `aclInfo.allowedPrincipals` in each document references either specific users (e.g., `user:sascha@doit.com`) or groups
- Discovery Engine consults the project’s ACL config (Google Workspace IDP) to evaluate access
- Gemini Enterprise “View as user” leverages the same ACL evaluation

## Operational Flow

```
+-----------+           +--------------------+           +----------------+
| Developer |  edits    | import_local_docs  |  calls    | Discovery      |
| (local)   |---------->| (manual trigger)   |---------->| Engine API     |
+-----------+           +--------------------+           +----------------+
       |                                                         |
       | watch_local_docs (optional)                             |
       |                                                         v
       |                                                   +------------+
       +-------------------------------------------------->| Datastore  |
                                                            +-----+------+
                                                                  |
                                                                  | served to
                                                                  v
                                                      +--------------------------+
                                                      | Gemini Enterprise UI     |
                                                      | (ACL-enforced search/RAG) |
                                                      +--------------------------+
```

Steps:
1. Developer updates `demo-content/` or `catalog.json`.
2. Run `tools/import_local_docs.py` (or let the watcher handle it) to push documents.
3. Discovery Engine ingests documents, stores them with metadata & ACLs.
4. Gemini Enterprise searches the datastore, applying ACLs using the configured identity provider.

## Key Files & Directories
- `demo-content/` – sample knowledge base
- `demo-content/catalog.json` – metadata + ACL assignment source of truth
- `tools/import_local_docs.py` – batch ingestion script
- `tools/watch_local_docs.py` – real-time watcher
- `scripts/smoke_search.sh` – curl-based search sanity check
- `setup.md` – operational checklist
- `custom-audience.md` – explains ACL mapping options

## Extensibility Considerations
- Swap `demo-content/` for a different source while retaining the same ingestion scripts.
- Replace direct user ACLs with Google Workspace groups or identity mappings as documented.
- Package the scripts into Cloud Run Jobs/Services for automated sync if needed.
- Use the same architecture to pipe conversions from external systems (Confluence exports, spreadsheets, etc.) by adjusting the transformer logic in `import_local_docs.py`.
