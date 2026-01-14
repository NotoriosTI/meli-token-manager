# Repository Guidelines

## Project Structure & Module Organization
- `src/meli_token_manager/` contains the core package (CLI entrypoint, token rotation, GCP secret storage, config loading).
- `config/config_vars.yaml.example` is the configuration template; copy to `config/config_vars.yaml` for local runs.
- `tokens.json` is the local token cache (do not commit real credentials).
- `README.md` documents usage flows (init, rotate, access token helpers).

## Build, Test, and Development Commands
- `poetry install` installs dependencies for local development.
- `poetry run python -m meli_token_manager.cli init --secret-origin gcp --config config/config_vars.yaml` performs the OAuth bootstrap and writes `tokens.json`.
- `poetry run python -m meli_token_manager.cli rotate --secret-origin gcp --config config/config_vars.yaml` runs the rotation loop.
- `poetry run meli-token-rotate --help` uses the packaged CLI script.
- `poetry build` produces a distributable package.

## Coding Style & Naming Conventions
- Indentation: 4 spaces, PEP 8 style.
- Naming: `snake_case` for functions/variables, `CapWords` for classes, `UPPER_SNAKE_CASE` for constants.
- Keep new modules under `src/meli_token_manager/` and follow existing import patterns (stdlib, third-party, local).
- No formatter is enforced; keep changes consistent with nearby code.

## Testing Guidelines
- Tests are not present yet; add them under `tests/` using `test_*.py` naming.
- Framework: `pytest` (dev dependency). Run with `poetry run pytest`.
- If adding coverage gates, wire them into CI and document in `README.md`.

## Commit & Pull Request Guidelines
- Recent commit messages are short, descriptive, and capitalized (e.g., “Added base package”). Follow that style unless asked otherwise.
- PRs should include a brief summary, testing notes, and any config changes (e.g., new required keys in `config/config_vars.yaml.example`).
- Never commit real tokens, client secrets, or GCP credentials.

## Security & Configuration Tips
- Keep `config/config_vars.yaml` and `tokens.json` local only; use `config/config_vars.yaml.example` for shared defaults.
- Set `SECRET_ORIGIN=gcp` and `GCP_PROJECT_ID` for production; rely on GCP Secret Manager as the source of truth.
