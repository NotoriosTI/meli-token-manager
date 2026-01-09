"""Thin wrapper over Google Secret Manager for create/update + read."""

from __future__ import annotations

from typing import Optional

from google.api_core import exceptions as gcp_exceptions
from google.cloud import secretmanager


class GCPSecretStorage:
    """Handles basic secret upsert/read operations in GCP Secret Manager."""

    def __init__(self, project_id: str) -> None:
        if not project_id:
            raise ValueError("project_id is required to talk to Secret Manager")
        self._project_id = project_id
        self._client = secretmanager.SecretManagerServiceClient()

    def _secret_path(self, secret_name: str) -> str:
        return self._client.secret_path(self._project_id, secret_name)

    def _latest_version_path(self, secret_name: str) -> str:
        return f"{self._secret_path(secret_name)}/versions/latest"

    def ensure_secret(self, secret_name: str) -> None:
        try:
            self._client.get_secret(name=self._secret_path(secret_name))
        except gcp_exceptions.NotFound:
            parent = f"projects/{self._project_id}"
            self._client.create_secret(
                parent=parent,
                secret_id=secret_name,
                secret=secretmanager.Secret(
                    replication=secretmanager.Replication(
                        automatic=secretmanager.Replication.Automatic()
                    )
                ),
            )

    def write_secret(self, secret_name: str, payload: bytes) -> str:
        """Create or update the secret and store the payload as a new version."""

        self.ensure_secret(secret_name)
        response = self._client.add_secret_version(
            parent=self._secret_path(secret_name),
            payload=secretmanager.SecretPayload(data=payload),
        )
        self._disable_prior_versions(secret_name, keep_version=response.name)
        return response.name

    def _disable_prior_versions(self, secret_name: str, keep_version: str) -> None:
        """Disable all other versions to avoid serving stale tokens."""

        parent = self._secret_path(secret_name)
        try:
            versions = self._client.list_secret_versions(request={"parent": parent})
        except gcp_exceptions.GoogleAPICallError:
            return

        for version in versions:
            if version.name == keep_version:
                continue
            if version.state == secretmanager.SecretVersion.State.ENABLED:
                try:
                    self._client.disable_secret_version(name=version.name)
                except gcp_exceptions.GoogleAPICallError:
                    continue

    def read_secret(self, secret_name: str) -> Optional[str]:
        """Read the latest version of a secret if it exists."""

        try:
            response = self._client.access_secret_version(
                name=self._latest_version_path(secret_name)
            )
        except gcp_exceptions.NotFound:
            return None
        payload = response.payload.data.decode("utf-8")
        return payload
