#!/usr/bin/env python3
"""Register a Vertex AI Agent Development Kit (ADK) agent with Gemini Enterprise.

This CLI wraps the Discovery Engine v1alpha API described in
`documentation/register-and-manage-an-adk-agent.txt` so you can expose the sample
agent from `../agent/agent.py` (or any ADK deployment) inside a Gemini Enterprise app.

Usage example:

    python register_agent.py \
        --project-id my-project \
        --app-id my-gemini-app \
        --display-name "Help Desk" \
        --description "Routes users to Billing or Support" \
        --adk-deployment-id 12345678901234567890 \
        --reasoning-engine-location us-central1

The script relies on Application Default Credentials (ADC). Run `gcloud auth login`
or set `GOOGLE_APPLICATION_CREDENTIALS` before executing this file.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

import google.auth
from google.auth.credentials import Credentials
from google.auth.transport.requests import AuthorizedSession

DEFAULT_SCOPES = ("https://www.googleapis.com/auth/cloud-platform",)
DEFAULT_LOCATION = "global"
DEFAULT_ENDPOINT = "global"


def _normalize_endpoint(endpoint: str) -> str:
    endpoint = endpoint.strip().rstrip("/")
    if endpoint.startswith("https://"):
        return endpoint
    if endpoint.endswith("-discoveryengine.googleapis.com"):
        return f"https://{endpoint}"
    base = endpoint.rstrip("-")
    if base not in {"global", "us", "eu"}:
        raise ValueError(
            "Endpoint must be global/us/eu, a value ending with "
            "'-discoveryengine.googleapis.com', or a full https:// URL."
        )
    return f"https://{base}-discoveryengine.googleapis.com"


def _load_icon_content(path: Path) -> str:
    data = path.read_bytes()
    return base64.b64encode(data).decode("ascii")


@dataclass
class AgentRegistrationConfig:
    project_id: str
    app_id: str
    display_name: str
    description: str
    reasoning_engine_location: Optional[str] = None
    adk_deployment_id: Optional[str] = None
    reasoning_engine_resource: Optional[str] = None
    location: str = DEFAULT_LOCATION
    endpoint: str = DEFAULT_ENDPOINT
    icon_uri: Optional[str] = None
    icon_content: Optional[str] = None
    authorization_ids: list[str] = field(default_factory=list)
    billing_project: Optional[str] = None

    def reasoning_engine(self) -> str:
        if self.reasoning_engine_resource:
            return self.reasoning_engine_resource
        if not self.reasoning_engine_location or not self.adk_deployment_id:
            raise ValueError(
                "Either --reasoning-engine-resource or both "
                "--reasoning-engine-location and --adk-deployment-id must be provided."
            )
        return (
            f"projects/{self.project_id}/locations/"
            f"{self.reasoning_engine_location}/reasoningEngines/{self.adk_deployment_id}"
        )

    def build_payload(self) -> dict:
        payload: dict = {
            "displayName": self.display_name,
            "description": self.description,
            "adkAgentDefinition": {
                "provisionedReasoningEngine": {
                    "reasoningEngine": self.reasoning_engine(),
                }
            },
        }
        if self.icon_uri:
            payload["icon"] = {"uri": self.icon_uri}
        elif self.icon_content:
            payload["icon"] = {"content": self.icon_content}

        if self.authorization_ids:
            payload["authorizationConfig"] = {
                "toolAuthorizations": [
                    f"projects/{self.project_id}/locations/global/authorizations/{auth_id}"
                    for auth_id in self.authorization_ids
                ]
            }
        return payload

    def registration_url(self) -> str:
        host = _normalize_endpoint(self.endpoint)
        return (
            f"{host}/v1alpha/projects/{self.project_id}"
            f"/locations/{self.location}"
            f"/collections/default_collection"
            f"/engines/{self.app_id}"
            f"/assistants/default_assistant/agents"
        )


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Register an ADK agent with Gemini Enterprise via the Discovery Engine API."
    )
    parser.add_argument("--project-id", help="Google Cloud project that hosts the Gemini Enterprise app.")
    parser.add_argument(
        "--billing-project",
        help="Optional project used for the X-Goog-User-Project header. Defaults to --project-id.",
    )
    parser.add_argument("--app-id", required=True, help="Gemini Enterprise app ID.")
    parser.add_argument("--display-name", required=True, help="User-facing name for the agent.")
    parser.add_argument("--description", required=True, help="Description shown in Gemini Enterprise.")
    parser.add_argument(
        "--location",
        default=DEFAULT_LOCATION,
        help="Gemini Enterprise app location (multi-region: global, us, or eu). Default: global.",
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=(
            "Endpoint location prefix or full Discovery Engine URL. "
            "Use global/us/eu or supply https://...discoveryengine.googleapis.com."
        ),
    )
    parser.add_argument(
        "--adk-deployment-id",
        help="Reasoning engine deployment ID from Vertex AI Agent Engine.",
    )
    parser.add_argument(
        "--reasoning-engine-location",
        help="Location (for example us-central1) where the ADK agent is deployed.",
    )
    parser.add_argument(
        "--reasoning-engine-resource",
        help="Full reasoning engine resource path. Overrides --adk-deployment-id/--reasoning-engine-location.",
    )
    icon_group = parser.add_mutually_exclusive_group()
    icon_group.add_argument("--icon-uri", help="Public URI for the agent icon.")
    icon_group.add_argument(
        "--icon-file",
        type=Path,
        help="Path to an image file. Contents are base64-encoded and sent via icon.content.",
    )
    parser.add_argument(
        "--authorization-id",
        action="append",
        default=[],
        help="Authorization resource ID (repeatable) for toolAuthorizations.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the request without calling the API.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print the HTTP response JSON.",
    )
    return parser.parse_args(argv)


def _obtain_credentials() -> tuple[Credentials, Optional[str]]:
    credentials, project_id = google.auth.default(scopes=DEFAULT_SCOPES)
    return credentials, project_id


def register_agent(
    config: AgentRegistrationConfig,
    credentials: Credentials,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict:
    payload = config.build_payload()
    url = config.registration_url()

    print(f"Registering agent '{config.display_name}' in app '{config.app_id}'...")
    print(f"Endpoint: {url}")
    if dry_run:
        print("--dry-run enabled; request body follows:\n" + json.dumps(payload, indent=2))
        return payload

    session = AuthorizedSession(credentials)
    headers = {
        "Content-Type": "application/json",
        "X-Goog-User-Project": config.billing_project or config.project_id,
    }
    response = session.post(url, headers=headers, json=payload, timeout=60)
    if response.status_code >= 400:
        raise RuntimeError(
            f"Registration failed with status {response.status_code}: {response.text}"
        )
    result = response.json()
    print("Agent registration request accepted.")
    if verbose:
        print(json.dumps(result, indent=2))
    else:
        print("Resource name:", result.get("name", "(not returned)"))
    return result


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    credentials, default_project = _obtain_credentials()
    project_id = args.project_id or default_project
    if not project_id:
        print(
            "Either provide --project-id or configure Application Default Credentials with a project.",
            file=sys.stderr,
        )
        return 1

    icon_content = _load_icon_content(args.icon_file) if args.icon_file else None
    config = AgentRegistrationConfig(
        project_id=project_id,
        billing_project=args.billing_project,
        app_id=args.app_id,
        display_name=args.display_name,
        description=args.description,
        location=args.location,
        endpoint=args.endpoint,
        adk_deployment_id=args.adk_deployment_id,
        reasoning_engine_location=args.reasoning_engine_location,
        reasoning_engine_resource=args.reasoning_engine_resource,
        icon_uri=args.icon_uri,
        icon_content=icon_content,
        authorization_ids=args.authorization_id,
    )

    if not config.reasoning_engine_resource and (
        not config.reasoning_engine_location or not config.adk_deployment_id
    ):
        print(
            "Provide either --reasoning-engine-resource or both --reasoning-engine-location "
            "and --adk-deployment-id.",
            file=sys.stderr,
        )
        return 1

    try:
        register_agent(config, credentials, dry_run=args.dry_run, verbose=args.verbose)
    except Exception as exc:  # noqa: BLE001 - surface helpful error to CLI users
        print(f"Error: {exc}", file=sys.stderr)
        if args.verbose:
            raise
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
