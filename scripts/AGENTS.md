# Scripts AGENTS

This folder contains local runtime and validation helper scripts.

## Runtime helpers

- `start.ps1` / `stop.ps1` are for Windows PowerShell.
- `start.sh` / `stop.sh` are for macOS and Linux shells.
- Start scripts run `docker compose up --build` from the project root.
- Stop scripts run `docker compose down` from the project root.

## Validation helpers

- `integration_test.py` performs basic route checks.
- `validate_part11_e2e.py` validates container auth, board persistence, AI, and relogin flows.

Keep scripts minimal and aligned with the documented Docker Compose flow.