"""CLI execution context and database path wiring."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import NoReturn

from capital_os.config import get_settings


# Trusted local CLI execution context constants
CLI_ACTOR_ID = "local-cli"
CLI_AUTHN_METHOD = "trusted_cli"
CLI_AUTHORIZATION_RESULT = "bypassed_trusted_channel"


def configure_db_path(db_path: str | None) -> None:
    """Configure the database path for local CLI execution.

    Sets the ``CAPITAL_OS_DB_URL`` env var and clears the cached settings so
    the next call to ``get_settings()`` picks up the new value.
    """
    if db_path is None:
        return

    path = Path(db_path)
    if not path.exists():
        _die(f"Database file not found: {db_path}")
    if not path.is_file():
        _die(f"Database path is not a file: {db_path}")

    os.environ["CAPITAL_OS_DB_URL"] = f"sqlite:///{path.resolve()}"
    get_settings.cache_clear()


def ensure_db_ready() -> None:
    """Verify the configured database is reachable."""
    try:
        from capital_os.db.session import transaction

        with transaction() as conn:
            conn.execute("SELECT 1 AS ok").fetchone()
    except Exception as exc:
        _die(f"Database not ready: {exc}")


def _die(message: str) -> NoReturn:
    """Emit structured error JSON to stderr and exit non-zero."""
    import json

    error = {"error": "cli_error", "message": message}
    sys.stderr.write(json.dumps(error) + "\n")
    raise SystemExit(1)
