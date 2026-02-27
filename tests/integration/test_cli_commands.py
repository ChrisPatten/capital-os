"""Integration tests for the capital-os CLI command surface.

All subprocess invocations use timeout=10 seconds to protect against hangs.

Covering:
- Root and nested --help smoke tests
- `health` command (success and bad-db-path error)
- `tool list` command
- `tool schema` command (known and unknown tool)
- `tool call` command (read tool, write tool, stdin, @file, validation failure)
- Exit-code discipline (0 success / 1 failure)
- Shell completion generation for bash, zsh, fish
- --db-path selection (valid path and missing/non-file path errors)
- CLI trusted-channel event-log context fields (actor_id, authn_method, authorization_result)
- HTTP / CLI adapter parity (identical output_hash for identical payload + state)
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Sequence

import pytest

from capital_os.config import get_settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CLI_CMD = "capital-os"
_TIMEOUT = 10  # seconds — protects against hung subprocesses

WRITE_TOOL = "create_account"
READ_TOOL = "list_accounts"


def _run(
    args: Sequence[str],
    *,
    input: str | None = None,
    timeout: int = _TIMEOUT,
) -> subprocess.CompletedProcess:
    """Run a capital-os CLI command and return the CompletedProcess."""
    return subprocess.run(
        [_CLI_CMD, *args],
        capture_output=True,
        text=True,
        input=input,
        timeout=timeout,
    )


def _db_path() -> str:
    """Return the absolute path to the current test SQLite file."""
    url = get_settings().db_url  # e.g. "sqlite:///./data/capital_os.db"
    raw = url.removeprefix("sqlite:///")
    return str(Path(raw).resolve())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_db(db_available: bool, clean_db) -> None:  # noqa: PT004
    """Ensure a clean migrated DB is present before each test.

    The session-level ``clean_db`` fixture (from conftest.py) handles this;
    we just declare it as a dependency so our autouse fixture runs after it.
    """


# ---------------------------------------------------------------------------
# --help smoke tests  (Task 1 / AC: 7)
# ---------------------------------------------------------------------------


def test_root_help_contains_commands() -> None:
    result = _run(["--help"])
    assert result.returncode == 0
    assert "health" in result.stdout
    assert "tool" in result.stdout
    assert "serve" in result.stdout


def test_health_help_smoke() -> None:
    result = _run(["health", "--help"])
    assert result.returncode == 0
    assert "--db-path" in result.stdout


def test_tool_help_smoke() -> None:
    result = _run(["tool", "--help"])
    assert result.returncode == 0
    assert "list" in result.stdout
    assert "schema" in result.stdout
    assert "call" in result.stdout


def test_tool_list_help_smoke() -> None:
    result = _run(["tool", "list", "--help"])
    assert result.returncode == 0
    assert "--db-path" in result.stdout


def test_tool_schema_help_smoke() -> None:
    result = _run(["tool", "schema", "--help"])
    assert result.returncode == 0
    assert "--db-path" in result.stdout


def test_tool_call_help_has_examples() -> None:
    result = _run(["tool", "call", "--help"])
    assert result.returncode == 0
    # Help text must include example content (from docstring)
    assert "stdin" in result.stdout.lower() or "example" in result.stdout.lower() or "--json" in result.stdout


def test_serve_help_smoke() -> None:
    result = _run(["serve", "--help"])
    assert result.returncode == 0
    assert "--host" in result.stdout
    assert "--port" in result.stdout


# ---------------------------------------------------------------------------
# health command (Task 3 / AC: 3)
# ---------------------------------------------------------------------------


def test_health_success(db_available: bool) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    result = _run(["health", "--db-path", _db_path()])
    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert body["status"] == "ok"
    assert "timestamp" in body


def test_health_bad_db_path_exits_nonzero(tmp_path: Path) -> None:
    """A nonexistent --db-path must produce structured stderr and exit 1."""
    missing = str(tmp_path / "nonexistent.db")
    result = _run(["health", "--db-path", missing])
    assert result.returncode != 0
    err = json.loads(result.stderr)
    assert "error" in err


def test_health_directory_as_db_path_exits_nonzero(tmp_path: Path) -> None:
    """A directory supplied as --db-path must produce structured stderr and exit 1."""
    result = _run(["health", "--db-path", str(tmp_path)])
    assert result.returncode != 0
    err = json.loads(result.stderr)
    assert "error" in err


# ---------------------------------------------------------------------------
# tool list (Task 3 / AC: 3)
# ---------------------------------------------------------------------------


def test_tool_list_returns_expected_structure(db_available: bool) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    result = _run(["tool", "list", "--db-path", _db_path()])
    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert "tools" in body
    assert "count" in body
    assert body["count"] == len(body["tools"])
    names = [t["name"] for t in body["tools"]]
    assert WRITE_TOOL in names
    assert READ_TOOL in names


def test_tool_list_contains_mode_field(db_available: bool) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    result = _run(["tool", "list", "--db-path", _db_path()])
    assert result.returncode == 0
    body = json.loads(result.stdout)
    for entry in body["tools"]:
        assert entry["mode"] in ("read", "write")


def test_tool_list_write_and_read_classification(db_available: bool) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    result = _run(["tool", "list", "--db-path", _db_path()])
    assert result.returncode == 0
    body = json.loads(result.stdout)
    by_name = {t["name"]: t for t in body["tools"]}
    assert by_name[WRITE_TOOL]["mode"] == "write"
    assert by_name[READ_TOOL]["mode"] == "read"


# ---------------------------------------------------------------------------
# tool schema (Task 3 / AC: 3)
# ---------------------------------------------------------------------------


def test_tool_schema_known_tool(db_available: bool) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    result = _run(["tool", "schema", WRITE_TOOL, "--db-path", _db_path()])
    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert body["tool"] == WRITE_TOOL
    assert "input_schema" in body
    assert "output_schema" in body


def test_tool_schema_unknown_tool_exits_nonzero(db_available: bool) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    result = _run(["tool", "schema", "not_a_real_tool", "--db-path", _db_path()])
    assert result.returncode != 0
    err = json.loads(result.stderr)
    assert "error" in err


# ---------------------------------------------------------------------------
# tool call -- read tool (Task 3, 4 / AC: 3, 4, 5, 6)
# ---------------------------------------------------------------------------


def test_tool_call_read_tool_inline_json(db_available: bool) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    payload = json.dumps({"correlation_id": "cli-read-001"})
    result = _run(
        ["tool", "call", READ_TOOL, "--json", payload, "--db-path", _db_path()],
    )
    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert "accounts" in body
    assert body["correlation_id"] == "cli-read-001"
    assert "output_hash" in body


def test_tool_call_read_tool_stdin(db_available: bool) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    payload = json.dumps({"correlation_id": "cli-stdin-001"})
    result = _run(
        ["tool", "call", READ_TOOL, "--db-path", _db_path()],
        input=payload,
    )
    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert body["correlation_id"] == "cli-stdin-001"


def test_tool_call_read_tool_json_file(db_available: bool, tmp_path: Path) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    payload_file = tmp_path / "payload.json"
    payload_file.write_text(json.dumps({"correlation_id": "cli-file-001"}))
    result = _run(
        [
            "tool", "call", READ_TOOL,
            "--json", f"@{payload_file}",
            "--db-path", _db_path(),
        ],
    )
    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert body["correlation_id"] == "cli-file-001"


def test_tool_call_get_account_balances_json_safe_date_output(db_available: bool) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    payload = json.dumps(
        {"as_of_date": "2026-02-01", "correlation_id": "cli-balances-json-safe-001"}
    )
    result = _run(
        ["tool", "call", "get_account_balances", "--json", payload, "--db-path", _db_path()],
    )
    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert isinstance(body["as_of_date"], str)
    assert body["correlation_id"] == "cli-balances-json-safe-001"


def test_tool_call_list_obligations_json_safe_decimal_output(db_available: bool) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    from capital_os.db.session import transaction
    from capital_os.domain.ledger.repository import create_account
    from capital_os.domain.ledger.service import create_or_update_obligation

    with transaction() as conn:
        account_id = create_account(conn, {"code": "cli-obl-9910", "name": "CLI Obligation Account", "account_type": "expense"})

    create_or_update_obligation(
        {
            "source_system": "cli-test",
            "name": "Internet",
            "account_id": account_id,
            "cadence": "monthly",
            "expected_amount": "125.5000",
            "variability_flag": False,
            "next_due_date": "2026-03-01",
            "metadata": {"category": "utilities"},
            "active": True,
            "correlation_id": "cli-obligation-seed-001",
        }
    )

    payload = json.dumps({"correlation_id": "cli-obligation-list-001"})
    result = _run(
        ["tool", "call", "list_obligations", "--json", payload, "--db-path", _db_path()],
    )
    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert body["correlation_id"] == "cli-obligation-list-001"
    assert len(body["obligations"]) == 1
    assert body["obligations"][0]["expected_amount"] == "125.5000"
    assert body["obligations"][0]["next_due_date"] == "2026-03-01"


# ---------------------------------------------------------------------------
# tool call -- write tool (Task 3, 4 / AC: 5)
# ---------------------------------------------------------------------------


def test_tool_call_write_tool_success(db_available: bool) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    payload = json.dumps({
        "code": "cli-test-9900",
        "name": "CLI Test Asset",
        "account_type": "asset",
        "correlation_id": "cli-write-001",
    })
    result = _run(
        ["tool", "call", WRITE_TOOL, "--json", payload, "--db-path", _db_path()],
    )
    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert body["status"] == "committed"
    assert body["correlation_id"] == "cli-write-001"
    assert body["output_hash"]


# ---------------------------------------------------------------------------
# Exit-code discipline (Task 4 / AC: 5, 6)
# ---------------------------------------------------------------------------


def test_tool_call_success_exits_zero(db_available: bool) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    payload = json.dumps({"correlation_id": "cli-exitcode-ok"})
    result = _run(
        ["tool", "call", READ_TOOL, "--json", payload, "--db-path", _db_path()],
    )
    assert result.returncode == 0


def test_tool_call_validation_failure_exits_nonzero(db_available: bool) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    # Missing required correlation_id
    payload = json.dumps({})
    result = _run(
        ["tool", "call", READ_TOOL, "--json", payload, "--db-path", _db_path()],
    )
    assert result.returncode != 0
    # Error must be on stderr, not stdout
    assert result.stdout == ""
    err = json.loads(result.stderr)
    assert err.get("error") == "validation_error"
    assert "details" in err


def test_tool_call_unknown_tool_exits_nonzero(db_available: bool) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    payload = json.dumps({"correlation_id": "cli-unknown-001"})
    result = _run(
        ["tool", "call", "no_such_tool", "--json", payload, "--db-path", _db_path()],
    )
    assert result.returncode != 0
    err = json.loads(result.stderr)
    assert "error" in err


def test_tool_call_no_payload_exits_nonzero(db_available: bool) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    # No --json, no stdin (subprocess with no input and stdout/stderr captured
    # makes stdin non-tty, so the CLI will try to read stdin and get EOF → empty string)
    result = _run(
        ["tool", "call", READ_TOOL, "--db-path", _db_path()],
        input="",  # Empty stdin
    )
    assert result.returncode != 0


def test_tool_call_invalid_json_exits_nonzero(db_available: bool) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    result = _run(
        ["tool", "call", READ_TOOL, "--json", "not-valid-json", "--db-path", _db_path()],
    )
    assert result.returncode != 0
    err = json.loads(result.stderr)
    assert "error" in err


def test_tool_call_json_file_not_found_exits_nonzero(db_available: bool) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    result = _run(
        [
            "tool", "call", READ_TOOL,
            "--json", "@/nonexistent/path/payload.json",
            "--db-path", _db_path(),
        ],
    )
    assert result.returncode != 0
    err = json.loads(result.stderr)
    assert "error" in err


def test_error_output_is_on_stderr_not_stdout(db_available: bool) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    payload = json.dumps({})  # Missing correlation_id
    result = _run(
        ["tool", "call", READ_TOOL, "--json", payload, "--db-path", _db_path()],
    )
    assert result.returncode != 0
    assert result.stdout == "", "Error output must not appear on stdout"
    assert result.stderr != "", "Error output must appear on stderr"


def test_success_output_is_on_stdout_not_stderr(db_available: bool) -> None:
    if not db_available:
        pytest.skip("database unavailable")

    payload = json.dumps({"correlation_id": "cli-stdio-check"})
    result = _run(
        ["tool", "call", READ_TOOL, "--json", payload, "--db-path", _db_path()],
    )
    assert result.returncode == 0
    assert result.stdout != "", "Success response must appear on stdout"
    assert result.stderr == "", "No error output expected on success"


# ---------------------------------------------------------------------------
# Shell completion (Task 5 / AC: 8)
# ---------------------------------------------------------------------------


def test_show_completion_bash() -> None:
    result = _run(["--show-completion", "bash"])
    assert result.returncode == 0
    assert len(result.stdout.strip()) > 0, "Expected non-empty completion script for bash"


def test_show_completion_zsh() -> None:
    result = _run(["--show-completion", "zsh"])
    assert result.returncode == 0
    assert len(result.stdout.strip()) > 0, "Expected non-empty completion script for zsh"


def test_show_completion_fish() -> None:
    result = _run(["--show-completion", "fish"])
    assert result.returncode == 0
    assert len(result.stdout.strip()) > 0, "Expected non-empty completion script for fish"


# ---------------------------------------------------------------------------
# --db-path selection (Task 6 / AC: 9, 10)
# ---------------------------------------------------------------------------


def test_db_path_valid_file_is_used(db_available: bool) -> None:
    """health --db-path pointing to the test DB should succeed."""
    if not db_available:
        pytest.skip("database unavailable")

    result = _run(["health", "--db-path", _db_path()])
    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert body["status"] == "ok"


def test_db_path_missing_file_returns_structured_error(tmp_path: Path) -> None:
    """A non-existent --db-path must produce structured stderr + non-zero exit."""
    missing_path = str(tmp_path / "does_not_exist.db")
    result = _run(["tool", "list", "--db-path", missing_path])
    assert result.returncode != 0
    err = json.loads(result.stderr)
    assert "error" in err
    assert "not found" in err.get("message", "").lower()


def test_db_path_directory_returns_structured_error(tmp_path: Path) -> None:
    """A directory supplied as --db-path must produce structured stderr + non-zero exit."""
    result = _run(["tool", "schema", READ_TOOL, "--db-path", str(tmp_path)])
    assert result.returncode != 0
    err = json.loads(result.stderr)
    assert "error" in err


# ---------------------------------------------------------------------------
# Event-log trusted CLI context fields (Task 3 / AC: 6 from story 15.1)
# ---------------------------------------------------------------------------


def test_cli_event_log_records_trusted_context(db_available: bool) -> None:
    """CLI invocations must persist actor_id, authn_method, authorization_result."""
    if not db_available:
        pytest.skip("database unavailable")

    corr_id = "cli-eventlog-context-001"
    payload = json.dumps({"correlation_id": corr_id})
    result = _run(
        ["tool", "call", READ_TOOL, "--json", payload, "--db-path", _db_path()],
    )
    assert result.returncode == 0

    db = _db_path()
    conn = sqlite3.connect(db)
    try:
        row = conn.execute(
            "SELECT actor_id, authn_method, authorization_result "
            "FROM event_log WHERE correlation_id = ? ORDER BY created_at DESC LIMIT 1",
            (corr_id,),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None, "Event log row must be present for CLI invocation"
    actor_id, authn_method, authorization_result = row
    assert actor_id == "local-cli"
    assert authn_method == "trusted_cli"
    assert authorization_result == "bypassed_trusted_channel"


# ---------------------------------------------------------------------------
# HTTP / CLI adapter output_hash parity (Tech-spec: Determinism and Parity)
# ---------------------------------------------------------------------------


def test_cli_http_output_hash_parity(db_available: bool) -> None:
    """Identical payload + DB state must yield identical output_hash via CLI and HTTP.

    For read tools, we run both adapters against the SAME DB state without resetting.
    Since list_accounts is non-mutating, both calls see identical state.
    """
    if not db_available:
        pytest.skip("database unavailable")

    from fastapi.testclient import TestClient
    from capital_os.api.app import app
    from tests.support.auth import AUTH_HEADERS

    corr_id = "cli-http-parity-001"
    payload = {"correlation_id": corr_id}

    # HTTP call
    client = TestClient(app, headers=AUTH_HEADERS)
    http_resp = client.post(f"/tools/{READ_TOOL}", json=payload)
    assert http_resp.status_code == 200
    http_hash = http_resp.json()["output_hash"]

    # CLI call on the SAME DB state (no reset - both see identical data)
    cli_result = _run(
        [
            "tool", "call", READ_TOOL,
            "--json", json.dumps(payload),
            "--db-path", _db_path(),
        ],
    )
    assert cli_result.returncode == 0
    cli_hash = json.loads(cli_result.stdout)["output_hash"]

    assert cli_hash == http_hash, (
        f"output_hash mismatch — CLI: {cli_hash!r}, HTTP: {http_hash!r}"
    )


# ---------------------------------------------------------------------------
# HTTP / CLI output_hash parity — write tool (AC: 1, 2)
# ---------------------------------------------------------------------------


def test_cli_http_output_hash_parity_write_tool(db_available: bool) -> None:
    """Identical idempotency key yields identical output_hash via CLI and HTTP.

    For write tools with idempotency (record_transaction_bundle), both calls
    share the same DB. The first call commits; the second sees idempotent-replay
    returning the stored canonical response and output_hash.
    """
    if not db_available:
        pytest.skip("database unavailable")

    from fastapi.testclient import TestClient
    from capital_os.api.app import app
    from capital_os.db.session import transaction
    from capital_os.domain.ledger.repository import create_account
    from tests.support.auth import AUTH_HEADERS

    # Seed accounts required for balanced postings
    with transaction() as conn:
        asset_id = create_account(conn, {"code": "parity-9910", "name": "Asset", "account_type": "asset"})
        equity_id = create_account(conn, {"code": "parity-9911", "name": "Equity", "account_type": "equity"})

    corr_id = "cli-http-parity-write-001"
    payload = {
        "source_system": "parity-test",
        "external_id": "tx-parity-001",
        "date": "2026-01-01T00:00:00Z",
        "description": "Parity test transaction",
        "postings": [
            {"account_id": asset_id, "amount": "100.0000", "currency": "USD"},
            {"account_id": equity_id, "amount": "-100.0000", "currency": "USD"},
        ],
        "correlation_id": corr_id,
    }

    # HTTP call → commits transaction
    client = TestClient(app, headers=AUTH_HEADERS)
    http_resp = client.post("/tools/record_transaction_bundle", json=payload)
    assert http_resp.status_code == 200
    http_body = http_resp.json()
    assert http_body["status"] == "committed"
    http_hash = http_body["output_hash"]

    # CLI call with SAME idempotency key → idempotent-replay returns stored hash
    cli_result = _run(
        [
            "tool", "call", "record_transaction_bundle",
            "--json", json.dumps(payload),
            "--db-path", _db_path(),
        ],
    )
    assert cli_result.returncode == 0
    cli_body = json.loads(cli_result.stdout)
    assert cli_body["status"] == "idempotent-replay"
    cli_hash = cli_body["output_hash"]

    assert cli_hash == http_hash, (
        f"write tool output_hash mismatch — CLI: {cli_hash!r}, HTTP: {http_hash!r}"
    )


# ---------------------------------------------------------------------------
# Non-object JSON payloads (AC: 4 — structured error for invalid payloads)
# ---------------------------------------------------------------------------


def test_tool_call_json_array_exits_nonzero(db_available: bool) -> None:
    """A valid JSON array payload (not an object) must be rejected."""
    if not db_available:
        pytest.skip("database unavailable")

    result = _run(
        ["tool", "call", READ_TOOL, "--json", "[1,2,3]", "--db-path", _db_path()],
    )
    assert result.returncode != 0
    err = json.loads(result.stderr)
    assert "error" in err
    assert "object" in err.get("message", "").lower()


def test_tool_call_json_string_exits_nonzero(db_available: bool) -> None:
    """A JSON string value (not an object) must be rejected."""
    if not db_available:
        pytest.skip("database unavailable")

    result = _run(
        ["tool", "call", READ_TOOL, "--json", '"hello"', "--db-path", _db_path()],
    )
    assert result.returncode != 0
    err = json.loads(result.stderr)
    assert "error" in err


# ---------------------------------------------------------------------------
# Event-log context fields on error paths
# ---------------------------------------------------------------------------


def test_cli_event_log_records_context_on_validation_error(db_available: bool) -> None:
    """Event log rows from CLI validation failures must record trusted context."""
    if not db_available:
        pytest.skip("database unavailable")

    corr_id = "cli-eventlog-valerr-001"
    # create_account missing required fields → ValidationError
    payload = json.dumps({
        "correlation_id": corr_id,
    })
    result = _run(
        ["tool", "call", WRITE_TOOL, "--json", payload, "--db-path", _db_path()],
    )
    assert result.returncode != 0

    db = _db_path()
    conn = sqlite3.connect(db)
    try:
        row = conn.execute(
            "SELECT actor_id, authn_method, authorization_result "
            "FROM event_log WHERE correlation_id = ? ORDER BY created_at DESC LIMIT 1",
            (corr_id,),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None, "Event log row must be present for CLI validation error"
    actor_id, authn_method, authorization_result = row
    assert actor_id == "local-cli"
    assert authn_method == "trusted_cli"
    assert authorization_result == "bypassed_trusted_channel"
