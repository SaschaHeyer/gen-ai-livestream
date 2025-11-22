import argparse
import json
from typing import List

from google.cloud import discoveryengine_v1 as discoveryengine


def load_documents(local_file: str) -> List[discoveryengine.Document]:
    """Read JSONL and turn each row into a Discovery Engine Document."""
    documents: List[discoveryengine.Document] = []
    with open(local_file, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            record = json.loads(line)

            doc = discoveryengine.Document()
            doc.id = record.get("id") or f"doc_{line_no}"
            if record.get("schemaId"):
                doc.schema_id = record["schemaId"]

            if "jsonData" in record:
                # Already stringified JSON that matches schema
                doc.json_data = record["jsonData"]
            elif "structData" in record:
                doc.struct_data = record["structData"]
            else:
                # Fallback: treat the entire row as struct_data
                doc.struct_data = record

            documents.append(doc)
    return documents


def import_documents(project_id: str, location: str, data_store_id: str, gcs_uri: str | None, local_file: str | None) -> None:
    client = discoveryengine.DocumentServiceClient()
    parent = client.branch_path(
        project=project_id,
        location=location,
        data_store=data_store_id,
        branch="default_branch",
    )

    if not gcs_uri and not local_file:
        raise ValueError("Provide either --gcs-uri or --local-file")

    if gcs_uri:
        print(f"Importing from GCS: {gcs_uri}")
        request = discoveryengine.ImportDocumentsRequest(
            parent=parent,
            gcs_source=discoveryengine.GcsSource(
                input_uris=[gcs_uri],
                data_schema="content",
            ),
            reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
        )
    else:
        documents = load_documents(local_file)
        print(f"Importing {len(documents)} documents from local file: {local_file}")
        inline_source = discoveryengine.ImportDocumentsRequest.InlineSource(documents=documents)
        request = discoveryengine.ImportDocumentsRequest(
            parent=parent,
            inline_source=inline_source,
            reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
        )

    operation = client.import_documents(request=request)
    print(f"Operation name: {operation.operation.name}")
    response = operation.result(timeout=600)

    # ImportDocumentsResponse currently surfaces errors in error_samples and error_config; counts live in metadata
    metadata = operation.metadata
    success = getattr(metadata, "success_count", None)
    failure = getattr(metadata, "failure_count", None)
    if success is not None and failure is not None:
        print(f"Success: {success}, Failures: {failure}")
    else:
        print("Import finished; counts not returned in response, check console if needed.")

    if failure and failure > 0:
        print("Failures detected. Check Vertex AI Search > Operations for detailed error rows.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest media docs into Vertex AI Media Search")
    parser.add_argument("--project-id", required=True, help="GCP Project ID (e.g. sascha-playground-doit)")
    parser.add_argument("--location", default="global", help="Location of the data store (default: global)")
    parser.add_argument("--data-store-id", required=True, help="Media data store ID")
    parser.add_argument("--gcs-uri", help="GCS URI of JSONL (use for large imports)")
    parser.add_argument("--local-file", default="data/media_data.jsonl", help="Local JSONL file (<=100 docs)")

    args = parser.parse_args()
    import_documents(args.project_id, args.location, args.data_store_id, args.gcs_uri, args.local_file)


if __name__ == "__main__":
    main()
