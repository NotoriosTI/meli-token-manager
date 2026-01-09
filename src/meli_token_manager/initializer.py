from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from .config_loader import DEFAULT_CONFIG_PATH, load_config
from .gcp_secret_storage import GCPSecretStorage

logger = logging.getLogger("meli-token-init")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")

TOKEN_ENDPOINT = "https://api.mercadolibre.com/oauth/token"
AUTH_URL = "https://auth.mercadolibre.cl/authorization"


def build_auth_url(app_id: str, redirect_uri: str) -> str:
    return f"{AUTH_URL}?response_type=code&client_id={app_id}&redirect_uri={redirect_uri}"


def _write_tokens_file(token_file: Path, token_data: Dict[str, Any]) -> None:
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(json.dumps(token_data, indent=2))


def bootstrap_tokens(
    *,
    auth_code: Optional[str] = None,
    config_path: str = DEFAULT_CONFIG_PATH,
    secret_origin: Optional[str] = None,
    gcp_project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Interactive (or provided code) bootstrap for first token acquisition."""

    config = load_config(
        config_path=config_path,
        secret_origin=secret_origin,
        gcp_project_id=gcp_project_id,
        auto_load=True,
    )

    app_id = config.require("MELI_APP_ID")
    client_secret = config.require("MELI_CLIENT_SECRET")
    redirect_uri = config.require("MELI_REDIRECT_URI")
    tokens_secret_name = config.require("MELI_TOKENS_SECRET_NAME")
    project_id = config.require("GCP_PROJECT_ID")
    token_file_path = Path(config.get("MELI_TOKEN_FILE", "tokens.json")).expanduser().resolve()

    url = build_auth_url(app_id, redirect_uri)
    if not auth_code:
        print("\n=== MercadoLibre OAuth Bootstrap ===")
        print("1) Visita y autoriza en:")
        print(f"\n{url}\n")
        auth_code = input("2) Pega el 'code' del redirect: ").strip()

    if not auth_code:
        raise RuntimeError("No auth code provided; cannot bootstrap tokens.")

    logger.info("Intercambiando code por tokens...")
    response = requests.post(
        TOKEN_ENDPOINT,
        data={
            "grant_type": "authorization_code",
            "client_id": app_id,
            "client_secret": client_secret,
            "code": auth_code,
            "redirect_uri": redirect_uri,
        },
        timeout=30,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:  # noqa: BLE001
        logger.error("Exchange failed: %s", response.text)
        raise RuntimeError("Failed to exchange authorization code") from exc

    tokens = response.json()
    _write_tokens_file(token_file_path, tokens)

    storage = GCPSecretStorage(project_id)
    storage.write_secret(tokens_secret_name, json.dumps(tokens, indent=2).encode("utf-8"))
    logger.info("Tokens guardados en %s y sincronizados en GCP", token_file_path)
    return tokens
