# Custom Audience Options

This note explains how to connect Gemini Enterprise ACLs to your personas and when to use each pattern.

## 1. Direct Google User ACLs (default)
- List each user explicitly in `allowedPrincipals`, e.g. `user:sascha@doit.com`.
- Works immediately after identity provider setup; no extra configuration required.
- Recommended when you have only a handful of demo users.

## 2. Google Workspace Groups
1. Create groups in the Admin console (for example `launch-ops-demo@doit.com`, `faq-readers-demo@doit.com`).
2. Add members to each group (`sascha@doit.com` → launch ops, `another-user@doit.com` → FAQ).
3. Update `demo-content/catalog.json` to reference the group emails with the `group:` prefix:
   ```json
   "allowedPrincipals": ["group:launch-ops-demo@doit.com"]
   ```
4. Re-run the import script so the new ACLs take effect:
   ```bash
   python tools/import_local_docs.py \
     --project sascha-playground-doit \
     --location global \
     --data-store-id demo_local_docs_acl_v1 \
     --content-root demo-content
   ```

## 3. External or Custom Identities (Identity Mapping Store)
Use this when your source system uses non-Google identities or application-specific roles.

### 3.1 Create the Identity Mapping Store
```bash
python - <<'PY'
from google.cloud import discoveryengine_v1alpha as de
project='sascha-playground-doit'
location='global'
ims_id='custom-demo-ims'
client = de.IdentityMappingStoreServiceClient()
parent = client.common_location_path(project, location)
store = client.create_identity_mapping_store(parent=parent, identity_mapping_store_id=ims_id)
print('Created IMS:', store.name)
PY
```

### 3.2 Import Identity Mappings
```bash
python - <<'PY'
from google.cloud import discoveryengine_v1alpha as de
project='sascha-playground-doit'
location='global'
ims_name=f'projects/{project}/locations/{location}/identityMappingStores/custom-demo-ims'
client = de.IdentityMappingStoreServiceClient()
entries = [
    de.IdentityMappingEntry(external_identity='launch_ops_group', user_id='sascha@doit.com'),
    de.IdentityMappingEntry(external_identity='faq_group', user_id='another-user@doit.com'),
]
request = de.ImportIdentityMappingsRequest(
    identity_mapping_store=ims_name,
    inline_source=de.ImportIdentityMappingsRequest.InlineSource(identity_mapping_entries=entries),
)
client.import_identity_mappings(request=request).result()
print('Imported identity mappings')
PY
```

### 3.3 Reference External Groups in Documents
- In `catalog.json`, reference the external group using the `external_group:` prefix:
  ```json
  "allowedPrincipals": ["group:external_group:launch_ops_group"]
  ```
- Recreate the datastore (or update its config) to point to the identity mapping store when calling `create_data_store`.
- Re-import documents so the new principals apply.

## When to Choose What?
- **Few demo users?** Stick with direct user ACLs (already deployed).
- **Multiple users per role?** Use Workspace groups for easier maintenance.
- **Non-Google identities?** Configure an identity mapping store and reference `external_group:*` entries.
