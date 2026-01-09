from __future__ import annotations

import argparse
import logging

from .initializer import bootstrap_tokens
from .rotator import DEFAULT_ROTATION_INTERVAL, refresh_once, run_rotation_loop

logger = logging.getLogger("meli-token-cli")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="MercadoLibre token manager (init + rotation)",
    )

    subparsers = parser.add_subparsers(dest="command")

    common = dict(
        config=dict(
            default="config/config_vars.yaml",
            help="Path to env-manager config file",
        ),
        secret_origin=dict(
            default=None,
            help="Force SECRET_ORIGIN (local|gcp). Defaults to env-manager resolution.",
        ),
        gcp_project_id=dict(
            default=None,
            help="Override GCP project id (otherwise read by env-manager)",
        ),
    )

    init_cmd = subparsers.add_parser("init", help="Bootstrap tokens via OAuth flow")
    init_cmd.add_argument("--config", **common["config"])
    init_cmd.add_argument("--secret-origin", **common["secret_origin"])
    init_cmd.add_argument("--gcp-project-id", **common["gcp_project_id"])
    init_cmd.add_argument(
        "--code",
        default=None,
        help="Authorization code from MercadoLibre redirect (omit for interactive prompt)",
    )

    rotate_cmd = subparsers.add_parser("rotate", help="Run rotation loop or single refresh")
    rotate_cmd.add_argument("--config", **common["config"])
    rotate_cmd.add_argument("--secret-origin", **common["secret_origin"])
    rotate_cmd.add_argument("--gcp-project-id", **common["gcp_project_id"])
    rotate_cmd.add_argument(
        "--once",
        action="store_true",
        help="Run a single refresh instead of the continuous loop",
    )
    rotate_cmd.add_argument(
        "--interval-seconds",
        type=int,
        default=DEFAULT_ROTATION_INTERVAL,
        help="Loop interval in seconds (only used without --once)",
    )

    parser.set_defaults(command="rotate")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
    args = parse_args()

    if args.command == "init":
        bootstrap_tokens(
            auth_code=args.code,
            config_path=args.config,
            secret_origin=args.secret_origin,
            gcp_project_id=args.gcp_project_id,
        )
        return

    if args.once:
        refresh_once(
            config_path=args.config,
            secret_origin=args.secret_origin,
            gcp_project_id=args.gcp_project_id,
        )
        return

    run_rotation_loop(
        config_path=args.config,
        secret_origin=args.secret_origin,
        gcp_project_id=args.gcp_project_id,
        interval_seconds=args.interval_seconds,
    )


if __name__ == "__main__":
    main()
