"""Helpers for loading configuration with env-manager.

The functions here always build a fresh ConfigManager so that any change in
Secret Manager is reflected on each call when required.
"""

from __future__ import annotations

from typing import Optional

from env_manager import ConfigManager

DEFAULT_CONFIG_PATH = "config/config_vars.yaml"


def load_config(
    *,
    config_path: str = DEFAULT_CONFIG_PATH,
    secret_origin: Optional[str] = None,
    gcp_project_id: Optional[str] = None,
    auto_load: bool = True,
    debug: bool = False,
) -> ConfigManager:
    """Build a new ConfigManager instance with the provided options."""

    return ConfigManager(
        config_path,
        secret_origin=secret_origin,
        gcp_project_id=gcp_project_id,
        auto_load=auto_load,
        debug=debug,
    )
