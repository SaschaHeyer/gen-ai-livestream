#!/usr/bin/env python3
"""Ingest local demo content into a Gemini Enterprise (Discovery Engine) datastore."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import pathlib
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from google.cloud import discoveryengine_v1alpha as discoveryengine
from google.protobuf import struct_pb2
from google.protobuf.json_format import MessageToDict

_LOGGER = logging.getLogger(__name__)
DEFAULT_BRANCH_ID = "0"


@dataclass
class CatalogEntry:
    doc_id: str
    path: pathlib.Path
    source_type: str
    owners: List[str]
    tags: List[str]
    allowed_principals: List[str]
    confidentiality: Optional[str]

    @classmethod
    def from_dict(cls, base_dir: pathlib.Path, payload: dict) -> "CatalogEntry":
        try:
            doc_id = str(payload["id"])
            rel_path = pathlib.Path(str(payload["path"]))
        except KeyError as exc:
            raise ValueError(f"Missing required catalog fields: {exc}") from exc

        return cls(
            doc_id=doc_id,
            path=base_dir / rel_path,
            source_type=str(payload.get("sourceType", "unknown")),
            owners=[str(o) for o in payload.get("owners", [])],
            tags=[str(t) for t in payload.get("tags", [])],
            allowed_principals=[str(p) for p in payload.get("allowedPrincipals", [])],
            confidentiality=(str(payload["confidentiality"]) if payload.get("confidentiality") else None),
        )


def load_catalog(catalog_path: pathlib.Path, content_root: pathlib.Path) -> List[CatalogEntry]:
    with catalog_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return [CatalogEntry.from_dict(content_root, item) for item in raw]


def read_file_content(entry: CatalogEntry) -> tuple[str, str]:
    suffix = entry.path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return entry.path.read_text(encoding="utf-8"), "text/plain"
    if suffix == ".txt":
        return entry.path.read_text(encoding="utf-8"), "text/plain"
    if suffix == ".csv":
        return csv_to_markdown(entry.path), "text/plain"
    raise ValueError(f"Unsupported file type for {entry.path}")


def csv_to_markdown(path: pathlib.Path) -> str:
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    lines = [f"# {path.stem.replace('-', ' ').title()}\n"]
    for row in rows:
        q = row.get("question") or row.get("Question")
        a = row.get("answer") or row.get("Answer")
        lines.append(f"## {q}\n")
        if a:
            lines.append(f"{a}\n")
    return "\n".join(lines).strip() + "\n"


def build_acl(entry: CatalogEntry) -> Optional[discoveryengine.Document.AclInfo]:
    if not entry.allowed_principals:
        return None
    principals = []
    for principal in entry.allowed_principals:
        if principal.startswith("user:"):
            principals.append(discoveryengine.Principal(user_id=principal.split(":", 1)[1]))
        elif principal.startswith("group:"):
            principals.append(discoveryengine.Principal(group_id=principal.split(":", 1)[1]))
        else:
            principals.append(discoveryengine.Principal(group_id=principal))
    restriction = discoveryengine.Document.AclInfo.AccessRestriction(principals=principals, idp_wide=False)
    return discoveryengine.Document.AclInfo(readers=[restriction])


def build_struct(entry: CatalogEntry, content: str) -> struct_pb2.Struct:
    stat = entry.path.stat()
    last_modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    struct_payload = {
        "sourceType": entry.source_type,
        "owners": entry.owners,
        "tags": entry.tags,
        "path": entry.path.as_posix(),
        "lastModified": last_modified,
        "body": content,
    }
    if entry.confidentiality:
        struct_payload["confidentiality"] = entry.confidentiality
    struct = struct_pb2.Struct()
    struct.update(struct_payload)
    return struct


def build_document(entry: CatalogEntry, skip_acl: bool) -> discoveryengine.Document:
    content, mime_type = read_file_content(entry)
    doc = discoveryengine.Document(
        id=entry.doc_id,
        struct_data=build_struct(entry, content),
        content=discoveryengine.Document.Content(
            raw_bytes=content.encode("utf-8"),
            mime_type=mime_type,
        ),
    )
    if not skip_acl:
        acl = build_acl(entry)
    else:
        acl = None
    if acl:
        doc.acl_info = acl
    return doc


def to_dict(document: discoveryengine.Document) -> dict:
    return MessageToDict(document._pb, preserving_proto_field_name=True)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--location", default="global")
    parser.add_argument("--data-store-id", required=True)
    parser.add_argument("--content-root", type=pathlib.Path, required=True)
    parser.add_argument("--catalog", type=pathlib.Path, default=None, help="Path to catalog.json (defaults to <content-root>/catalog.json)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-acl", action="store_true", help="Omit ACL information (useful if identity provider not configured yet).")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def import_documents(project: str, location: str, data_store_id: str, documents: Iterable[discoveryengine.Document]) -> discoveryengine.ImportDocumentsResponse:
    client_options = None
    if location != "global":
        client_options = {"api_endpoint": f"{location}-discoveryengine.googleapis.com"}
    client = discoveryengine.DocumentServiceClient(client_options=client_options)
    parent = client.branch_path(project, location, data_store_id, DEFAULT_BRANCH_ID)
    inline_source = discoveryengine.ImportDocumentsRequest.InlineSource(documents=list(documents))
    request = discoveryengine.ImportDocumentsRequest(
        parent=parent,
        inline_source=inline_source,
        auto_generate_ids=False,
        reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
    )
    operation = client.import_documents(request=request)
    _LOGGER.info("Import operation %s started", operation.operation.name)
    result = operation.result()
    return result


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s:%(message)s")

    content_root = args.content_root.resolve()
    if not content_root.exists():
        _LOGGER.error("Content root %s does not exist", content_root)
        return 1

    catalog_path = (args.catalog or content_root / "catalog.json").resolve()
    entries = load_catalog(catalog_path, content_root)
    documents = [build_document(entry, skip_acl=args.skip_acl) for entry in entries]

    if args.dry_run:
        payload = [to_dict(doc) for doc in documents]
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    result = import_documents(args.project, args.location, args.data_store_id, documents)
    errors = [MessageToDict(sample, preserving_proto_field_name=True) for sample in result.error_samples]
    summary = {
        "success_count": len(documents) - len(result.error_samples),
        "error_count": len(result.error_samples),
        "errors": errors,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
