from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from .config_loader import DEFAULT_CONFIG_PATH, load_config
from .gcp_secret_storage import GCPSecretStorage

logger = logging.getLogger("meli-token-rotator")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")

DEFAULT_ROTATION_INTERVAL = 4 * 60 * 60  # 4 hours to stay ahead of the 6h expiry
TOKEN_ENDPOINT = "https://api.mercadolibre.com/oauth/token"


class TokenRotator:
    """Handles MercadoLibre token refresh and storage in local disk + GCP."""

    def __init__(
        self,
        *,
        config_path: str = DEFAULT_CONFIG_PATH,
        secret_origin: Optional[str] = None,
        gcp_project_id: Optional[str] = None,
    ) -> None:
        self._config = load_config(
            config_path=config_path,
            secret_origin=secret_origin,
            gcp_project_id=gcp_project_id,
            auto_load=True,
        )

        self._app_id = self._config.require("MELI_APP_ID")
        self._client_secret = self._config.require("MELI_CLIENT_SECRET")
        self._tokens_secret_name = self._config.require("MELI_TOKENS_SECRET_NAME")
        self._project_id = self._config.require("GCP_PROJECT_ID")

        token_file = self._config.get("MELI_TOKEN_FILE", "tokens.json")
        self._token_file = Path(token_file).expanduser().resolve()
        self.rotation_interval_seconds = int(
            self._config.get("ROTATION_INTERVAL_SECONDS", DEFAULT_ROTATION_INTERVAL)
        )

        self._secret_storage = GCPSecretStorage(self._project_id)
        self._tokens: Dict[str, Any] = self._bootstrap_tokens()

    def _bootstrap_tokens(self) -> Dict[str, Any]:
        tokens = self._load_tokens_from_file()
        if tokens:
            return tokens

        tokens = self._load_tokens_from_secret()
        if tokens:
            self._write_tokens_file(tokens)
            return tokens

        raise RuntimeError(
            "No existing tokens found. Run the initializer to obtain the first token set."
        )

    def _load_tokens_from_file(self) -> Dict[str, Any]:
        if not self._token_file.exists():
            return {}
        try:
            return json.loads(self._token_file.read_text())
        except Exception as exc:  # noqa: BLE001 - want to log and continue
            logger.warning("Failed to read tokens from %s: %s", self._token_file, exc)
            return {}

    def _load_tokens_from_secret(self) -> Dict[str, Any]:
        payload = self._secret_storage.read_secret(self._tokens_secret_name)
        if not payload:
            return {}
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            logger.error(
                "Secret %s exists but is not valid JSON: %s",
                self._tokens_secret_name,
                exc,
            )
            return {}

    def _write_tokens_file(self, token_data: Dict[str, Any]) -> None:
        self._token_file.parent.mkdir(parents=True, exist_ok=True)
        self._token_file.write_text(json.dumps(token_data, indent=2))

    def _request_refresh(self, refresh_token: str) -> Dict[str, Any]:
        response = requests.post(
            TOKEN_ENDPOINT,
            data={
                "grant_type": "refresh_token",
                "client_id": self._app_id,
                "client_secret": self._client_secret,
                "refresh_token": refresh_token,
            },
            timeout=15,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:  # noqa: BLE001
            logger.error("Refresh request failed: %s", response.text)
            raise RuntimeError("Token refresh failed") from exc
        return response.json()

    def refresh_once(self) -> Dict[str, Any]:
        refresh_token = self._tokens.get("refresh_token") or self._config.require(
            "MELI_REFRESH_TOKEN"
        )
        payload = self._request_refresh(refresh_token)
        now = int(time.time())

        token_data: Dict[str, Any] = {
            "access_token": payload.get("access_token"),
            "refresh_token": payload.get("refresh_token") or refresh_token,
            "token_type": payload.get("token_type"),
            "scope": payload.get("scope"),
            "expires_in": payload.get("expires_in"),
            "updated_at": now,
        }

        expires_in = payload.get("expires_in")
        if expires_in:
            token_data["expires_at"] = now + int(expires_in)

        if not token_data.get("access_token"):
            raise RuntimeError("No access_token returned by MercadoLibre")

        self._tokens = token_data
        self._write_tokens_file(token_data)
        self._secret_storage.write_secret(
            self._tokens_secret_name, json.dumps(token_data, indent=2).encode("utf-8")
        )
        logger.info("Tokens refreshed; latest version enabled and prior versions disabled in GCP")
        return token_data

    def run_forever(self, *, interval_seconds: Optional[int] = None) -> None:
        """Refresh tokens every interval. Intended for cron/supervisor usage."""

        interval = interval_seconds or self.rotation_interval_seconds or DEFAULT_ROTATION_INTERVAL
        while True:
            try:
                self.refresh_once()
            except Exception as exc:  # noqa: BLE001 - keep loop alive
                logger.error("Token refresh failed: %s", exc)
                time.sleep(min(600, interval))
                continue
            time.sleep(interval)


def refresh_once(
    *,
    config_path: str = DEFAULT_CONFIG_PATH,
    secret_origin: Optional[str] = None,
    gcp_project_id: Optional[str] = None,
) -> Dict[str, Any]:
    rotator = TokenRotator(
        config_path=config_path,
        secret_origin=secret_origin,
        gcp_project_id=gcp_project_id,
    )
    return rotator.refresh_once()


def run_rotation_loop(
    *,
    config_path: str = DEFAULT_CONFIG_PATH,
    secret_origin: Optional[str] = None,
    gcp_project_id: Optional[str] = None,
    interval_seconds: Optional[int] = None,
) -> None:
    rotator = TokenRotator(
        config_path=config_path,
        secret_origin=secret_origin,
        gcp_project_id=gcp_project_id,
    )
    rotator.run_forever(interval_seconds=interval_seconds)
