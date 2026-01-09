"""Helpers to fetch the latest token from GCP Secret Manager.

env-manager is executed on each call so that fresh values (secret names,
project IDs, and the secret itself) are always loaded.
"""

from __future__ import annotations

import json
from typing import Dict, Optional

from .config_loader import DEFAULT_CONFIG_PATH, load_config
from .gcp_secret_storage import GCPSecretStorage


def get_token_payload(
    *,
    config_path: str = DEFAULT_CONFIG_PATH,
    secret_origin: Optional[str] = None,
    gcp_project_id: Optional[str] = None,
) -> Dict[str, str]:
    """Return the JSON payload stored in Secret Manager.

    A new ConfigManager is built on every call to avoid serving stale secrets.
    """

    config = load_config(
        config_path=config_path,
        secret_origin=secret_origin,
        gcp_project_id=gcp_project_id,
        auto_load=True,
    )
    secret_name = config.require("MELI_TOKENS_SECRET_NAME")
    project_id = config.require("GCP_PROJECT_ID")

    storage = GCPSecretStorage(project_id)
    payload = storage.read_secret(secret_name)
    if not payload:
        raise RuntimeError(f"Secret '{secret_name}' not found in project '{project_id}'")
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Secret '{secret_name}' contains invalid JSON; refresh the token first"
        ) from exc


def get_access_token(
    *,
    config_path: str = DEFAULT_CONFIG_PATH,
    secret_origin: Optional[str] = None,
    gcp_project_id: Optional[str] = None,
) -> str:
    """Return the latest access token from GCP Secret Manager."""

    data = get_token_payload(
        config_path=config_path,
        secret_origin=secret_origin,
        gcp_project_id=gcp_project_id,
    )
    token = data.get("access_token")
    if not token:
        raise RuntimeError("No access_token stored in Secret Manager")
    return token

if __name__ == "__main__":
    access_token = get_access_token(
        config_path="config/config_vars.yaml",
        secret_origin="gcp",
        gcp_project_id="notorios",
    )
    print(access_token)