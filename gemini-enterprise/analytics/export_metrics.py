#!/usr/bin/env python3
"""CLI helper to export Gemini Enterprise analytics into BigQuery."""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any, Dict, Optional

import google.auth
from google.auth.transport.requests import AuthorizedSession


DISCOVERY_API_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export Gemini Enterprise analytics to BigQuery."
    )
    parser.add_argument("--project-id", required=True, help="Google Cloud project ID.")
    parser.add_argument(
        "--location",
        required=True,
        help="Gemini Enterprise multi-region (global, us, eu).",
    )
    parser.add_argument(
        "--app-id", required=True, help="Gemini Enterprise app/engine identifier."
    )
    parser.add_argument(
        "--dataset-id",
        required=True,
        help="Target BigQuery dataset ID (without the project prefix).",
    )
    parser.add_argument(
        "--table-id",
        required=True,
        help="Target BigQuery table ID (without project or dataset prefix).",
    )
    parser.add_argument(
        "--billing-project",
        help="Optional billing/quota project for X-Goog-User-Project header.",
    )
    parser.add_argument(
        "--endpoint-host",
        help=(
            "Fully-qualified discoveryengine API host "
            "(defaults to <location>-discoveryengine.googleapis.com)."
        ),
    )
    parser.add_argument(
        "--operation-name",
        help="Skip creating a new export and resume polling a prior operation.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=20,
        help="Interval between LRO status checks (seconds).",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=900,
        help="Overall timeout for waiting on the export operation.",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Return immediately after kicking off the export operation.",
    )
    return parser.parse_args()


def resolve_host(location: str, override: Optional[str]) -> str:
    if override:
        return override
    prefix_map = {"global": "global-", "us": "us-", "eu": "eu-"}
    normalized = location.lower()
    prefix = prefix_map.get(normalized, f"{normalized}-")
    return f"{prefix}discoveryengine.googleapis.com"


def base_url(host: str) -> str:
    return f"https://{host}/v1alpha"


def default_session() -> AuthorizedSession:
    credentials, _ = google.auth.default(scopes=[DISCOVERY_API_SCOPE])
    return AuthorizedSession(credentials)


def analytics_resource(project_id: str, location: str, app_id: str) -> str:
    return (
        f"projects/{project_id}/locations/{location}"
        f"/collections/default_collection/engines/{app_id}/analytics"
    )


def trigger_export(
    session: AuthorizedSession,
    base_api_url: str,
    analytics_path: str,
    dataset_id: str,
    table_id: str,
    billing_project: str,
) -> str:
    url = f"{base_api_url}/{analytics_path}:exportMetrics"
    payload: Dict[str, Any] = {
        "analytics": analytics_path,
        "outputConfig": {
            "bigqueryDestination": {
                "datasetId": dataset_id,
                "tableId": table_id,
            }
        },
    }
    headers = {"X-Goog-User-Project": billing_project}
    response = session.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    name = data.get("name")
    if not name:
        raise RuntimeError(f"Unexpected API response: {data}")
    return name


def wait_for_operation(
    session: AuthorizedSession,
    base_api_url: str,
    operation_name: str,
    billing_project: str,
    poll_seconds: int,
    timeout_seconds: int,
) -> Dict[str, Any]:
    headers = {"X-Goog-User-Project": billing_project}
    deadline = time.time() + timeout_seconds if timeout_seconds > 0 else None
    status_url = f"{base_api_url}/{operation_name}"
    while True:
        response = session.get(status_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("done"):
            if "error" in data:
                detail = data["error"]
                raise RuntimeError(
                    f"Export failed: {detail.get('message', detail)}"
                )
            return data
        if deadline is not None and time.time() >= deadline:
            raise TimeoutError(
                f"Operation {operation_name} did not finish within {timeout_seconds}s"
            )
        time.sleep(max(1, poll_seconds))


def main() -> int:
    args = parse_args()
    billing_project = args.billing_project or args.project_id
    host = resolve_host(args.location, args.endpoint_host)
    api_base = base_url(host)
    session = default_session()

    try:
        if args.operation_name:
            operation_name = args.operation_name
            print(f"[analytics] Resuming operation: {operation_name}")
        else:
            analytics_path = analytics_resource(
                args.project_id, args.location, args.app_id
            )
            operation_name = trigger_export(
                session,
                api_base,
                analytics_path,
                args.dataset_id,
                args.table_id,
                billing_project,
            )
            print(
                "[analytics] Export started:\n"
                f"  analytics: {analytics_path}\n"
                f"  dataset:   {args.dataset_id}\n"
                f"  table:     {args.table_id}\n"
                f"  operation: {operation_name}"
            )

        if args.no_wait:
            print("[analytics] --no-wait supplied; exiting without polling.")
            return 0

        poll_result = wait_for_operation(
            session,
            api_base,
            operation_name,
            billing_project,
            args.poll_seconds,
            args.timeout_seconds,
        )
        response = poll_result.get("response", {})
        print("[analytics] Export completed successfully.")
        if response:
            print(response)
    except Exception as exc:  # noqa: BLE001
        print(f"[analytics] ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
