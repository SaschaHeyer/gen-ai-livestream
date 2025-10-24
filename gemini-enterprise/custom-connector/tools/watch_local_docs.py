#!/usr/bin/env python3
"""Watch the demo content folder and upsert changed documents into the datastore."""

from __future__ import annotations

import argparse
import asyncio
import logging
import pathlib
import sys
from typing import Dict, Optional

from watchfiles import awatch, Change

from import_local_docs import (  # type: ignore
    CatalogEntry,
    build_document,
    import_documents,
    load_catalog,
)

_LOGGER = logging.getLogger(__name__)


def build_path_index(entries: list[CatalogEntry]) -> Dict[pathlib.Path, CatalogEntry]:
    return {entry.path.resolve(): entry for entry in entries}


async def handle_events(project: str, location: str, data_store_id: str, index: Dict[pathlib.Path, CatalogEntry], skip_acl: bool, *paths: pathlib.Path) -> None:
    docs = []
    for path in paths:
        entry = index.get(path.resolve())
        if not entry:
            _LOGGER.debug("Ignoring change for %s (not in catalog)", path)
            continue
        _LOGGER.info("Rebuilding document %s", entry.doc_id)
        docs.append(build_document(entry, skip_acl=skip_acl))
    if not docs:
        return
    result = import_documents(project, location, data_store_id, docs)
    if result.error_samples:
        _LOGGER.error("Upsert completed with %d errors", len(result.error_samples))
    else:
        _LOGGER.info("Upserted %d document(s)", len(docs))


async def watch_loop(project: str, location: str, data_store_id: str, content_root: pathlib.Path, catalog_path: pathlib.Path, skip_acl: bool) -> None:
    entries = load_catalog(catalog_path, content_root)
    index = build_path_index(entries)
    _LOGGER.info("Watching %s for changes", content_root)
    async for changes in awatch(content_root, recursive=True):
        changed_paths = [pathlib.Path(path) for change, path in changes if change in {Change.modified, Change.added}]
        if not changed_paths:
            continue
        await handle_events(project, location, data_store_id, index, skip_acl, *changed_paths)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--location", default="global")
    parser.add_argument("--data-store-id", required=True)
    parser.add_argument("--content-root", type=pathlib.Path, required=True)
    parser.add_argument("--catalog", type=pathlib.Path, default=None)
    parser.add_argument("--skip-acl", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s:%(message)s")
    content_root = args.content_root.resolve()
    if not content_root.exists():
        _LOGGER.error("Content root %s does not exist", content_root)
        return 1
    catalog_path = (args.catalog or content_root / "catalog.json").resolve()
    try:
        asyncio.run(watch_loop(args.project, args.location, args.data_store_id, content_root, catalog_path, args.skip_acl))
    except KeyboardInterrupt:
        _LOGGER.info("Watcher stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
