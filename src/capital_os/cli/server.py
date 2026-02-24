"""CLI command to start the HTTP server."""

from __future__ import annotations

from typing import Annotated, Optional

import typer

server_app = typer.Typer(
    name="serve",
    help="Start the Capital OS HTTP server.",
    invoke_without_command=True,
)


@server_app.callback(invoke_without_command=True)
def serve(
    host: Annotated[str, typer.Option(help="Bind address.")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Bind port.")] = 8000,
    db_path: Annotated[
        Optional[str],
        typer.Option("--db-path", help="Path to SQLite database file."),
    ] = None,
) -> None:
    """Start the Capital OS FastAPI server.

    Example:

        capital-os serve

        capital-os serve --host 0.0.0.0 --port 9000
    """
    if db_path is not None:
        from capital_os.cli.context import configure_db_path as _configure_db
        _configure_db(db_path)

    import uvicorn
    uvicorn.run("capital_os.api.app:app", host=host, port=port)
