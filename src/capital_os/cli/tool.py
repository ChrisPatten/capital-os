"""CLI commands for tool discovery and invocation."""

from __future__ import annotations

import json
import sys
from typing import Annotated, NoReturn, Optional

import typer

from capital_os.cli.context import (
    CLI_ACTOR_ID,
    CLI_AUTHN_METHOD,
    CLI_AUTHORIZATION_RESULT,
    configure_db_path,
)
from capital_os.runtime.execute_tool import (
    TOOL_HANDLERS,
    WRITE_TOOLS,
    execute_tool,
    tool_names,
)

tool_app = typer.Typer(
    name="tool",
    help="Discover and invoke Capital OS tools locally.",
    no_args_is_help=True,
)


# ── tool list ─────────────────────────────────────────────────────────

@tool_app.command("list")
def tool_list(
    db_path: Annotated[
        Optional[str],
        typer.Option("--db-path", help="Path to SQLite database file."),
    ] = None,
) -> None:
    """List all registered tool names.

    Example:

        capital-os tool list
    """
    configure_db_path(db_path)
    names = tool_names()
    output = {
        "tools": [
            {
                "name": name,
                "mode": "write" if name in WRITE_TOOLS else "read",
            }
            for name in names
        ],
        "count": len(names),
    }
    sys.stdout.write(json.dumps(output, indent=2) + "\n")


# ── tool schema ───────────────────────────────────────────────────────

# Mapping from tool handler module to (InputSchema, OutputSchema) class names.
# We introspect at runtime so no large import at module level.

def _get_tool_schemas(tool_name: str) -> tuple[type, type] | None:
    """Return (InputSchema, OutputSchema) for a tool, or None if unknown."""
    if tool_name not in TOOL_HANDLERS:
        return None

    from capital_os.schemas import tools as schema_mod

    # Convention: tool "foo_bar" → FooBarIn / FooBarOut
    class_stem = "".join(word.capitalize() for word in tool_name.split("_"))
    in_cls = getattr(schema_mod, f"{class_stem}In", None)
    out_cls = getattr(schema_mod, f"{class_stem}Out", None)
    if in_cls is None or out_cls is None:
        return None
    return in_cls, out_cls


@tool_app.command("schema")
def tool_schema(
    tool_name: Annotated[str, typer.Argument(help="Name of the tool.")],
    db_path: Annotated[
        Optional[str],
        typer.Option("--db-path", help="Path to SQLite database file."),
    ] = None,
) -> None:
    """Display input/output JSON schema for a tool.

    Example:

        capital-os tool schema create_account
    """
    configure_db_path(db_path)

    if tool_name not in TOOL_HANDLERS:
        _error_exit(f"Unknown tool: {tool_name}")

    schemas = _get_tool_schemas(tool_name)
    output: dict = {"tool": tool_name}
    if schemas:
        in_cls, out_cls = schemas
        output["input_schema"] = in_cls.model_json_schema()
        output["output_schema"] = out_cls.model_json_schema()
    else:
        output["note"] = "Schema introspection unavailable for this tool."

    sys.stdout.write(json.dumps(output, indent=2) + "\n")


# ── tool call ─────────────────────────────────────────────────────────

@tool_app.command("call")
def tool_call(
    tool_name: Annotated[str, typer.Argument(help="Name of the tool to invoke.")],
    json_payload: Annotated[
        Optional[str],
        typer.Option(
            "--json",
            help=(
                "JSON payload: inline string or @filename. "
                "Reads stdin when omitted and stdin is piped."
            ),
        ),
    ] = None,
    db_path: Annotated[
        Optional[str],
        typer.Option("--db-path", help="Path to SQLite database file."),
    ] = None,
) -> None:
    """Invoke a Capital OS tool locally (trusted channel).

    Examples:

        capital-os tool call list_accounts --json '{"correlation_id":"c1"}'

        capital-os tool call create_account --json @payload.json

        echo '{"correlation_id":"c1"}' | capital-os tool call list_accounts
    """
    configure_db_path(db_path)

    payload = _resolve_payload(json_payload)

    result = execute_tool(
        tool_name,
        payload,
        actor_id=CLI_ACTOR_ID,
        authn_method=CLI_AUTHN_METHOD,
        authorization_result=CLI_AUTHORIZATION_RESULT,
    )

    if result.success:
        sys.stdout.write(json.dumps(result.payload, indent=2) + "\n")
        raise SystemExit(0)

    sys.stderr.write(json.dumps(result.payload, indent=2) + "\n")
    raise SystemExit(1)


# ── helpers ───────────────────────────────────────────────────────────

def _resolve_payload(json_payload: str | None) -> dict:
    """Resolve JSON payload from --json value, @file, or stdin."""
    raw: str | None = None

    if json_payload is not None:
        if json_payload.startswith("@"):
            file_path = json_payload[1:]
            try:
                with open(file_path) as f:
                    raw = f.read()
            except FileNotFoundError:
                _error_exit(f"Payload file not found: {file_path}")
            except OSError as exc:
                _error_exit(f"Cannot read payload file: {exc}")
        else:
            raw = json_payload
    elif not sys.stdin.isatty():
        raw = sys.stdin.read()
    else:
        _error_exit(
            "No payload provided. Use --json '{...}', --json @file, or pipe to stdin."
        )

    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        _error_exit(f"Invalid JSON payload: {exc}")

    if not isinstance(parsed, dict):
        _error_exit("Payload must be a JSON object.")

    return parsed


def _error_exit(message: str) -> NoReturn:
    """Write structured error to stderr and exit non-zero."""
    error = {"error": "cli_error", "message": message}
    sys.stderr.write(json.dumps(error) + "\n")
    raise SystemExit(1)
