"""Capital OS CLI - trusted local operator interface.

Invoke Capital OS tools locally without running the HTTP server.
All core invariants (validation, hashing, event logging, transaction
boundaries) are preserved through the shared runtime executor.

Examples:

    capital-os health

    capital-os tool list

    capital-os tool call list_accounts --json '{"correlation_id":"c1"}'

    capital-os serve
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Annotated, Optional

import typer

from capital_os.cli.context import configure_db_path, ensure_db_ready
from capital_os.cli.server import server_app
from capital_os.cli.tool import tool_app

app = typer.Typer(
    name="capital-os",
    help="Capital OS - deterministic financial truth layer CLI.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

app.add_typer(tool_app, name="tool")
app.add_typer(server_app, name="serve")


@app.command()
def health(
    db_path: Annotated[
        Optional[str],
        typer.Option("--db-path", help="Path to SQLite database file."),
    ] = None,
) -> None:
    """Check database connectivity and runtime readiness.

    Example:

        capital-os health

        capital-os health --db-path /tmp/test.db
    """
    configure_db_path(db_path)
    try:
        ensure_db_ready()
    except SystemExit:
        raise
    except Exception as exc:
        error = {"error": "health_check_failed", "message": str(exc)}
        sys.stderr.write(json.dumps(error) + "\n")
        raise SystemExit(1)

    result = {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
    sys.stdout.write(json.dumps(result, indent=2) + "\n")
