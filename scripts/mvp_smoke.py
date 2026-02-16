#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib import error, request


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_DB_URL = "sqlite:///./data/capital_os.db"
DEFAULT_AUTH_TOKEN = "dev-admin-token"
SMOKE_SOURCE_SYSTEM = "mvp-smoke"
SMOKE_EXTERNAL_ID = "smoke-tx-001"
SMOKE_OBLIGATION_NAME = "Smoke Obligation"
SMOKE_ACCOUNT_ASSET = "ast_cash_citizens_checking_7819"
SMOKE_ACCOUNT_EQUITY = "eq_opening_balances"


class StepFailure(RuntimeError):
    def __init__(self, step: str, message: str):
        super().__init__(message)
        self.step = step


def _env() -> dict[str, str]:
    env = os.environ.copy()
    if not env.get("CAPITAL_OS_DB_URL"):
        env["CAPITAL_OS_DB_URL"] = DEFAULT_DB_URL
    if not env.get("BASE_URL"):
        env["BASE_URL"] = DEFAULT_BASE_URL
    if not env.get("CAPITAL_OS_AUTH_TOKEN"):
        env["CAPITAL_OS_AUTH_TOKEN"] = DEFAULT_AUTH_TOKEN
    return env


def _run_step(step: str, command: list[str], env: dict[str, str]) -> None:
    print(f"[mvp-smoke] STEP {step}: {' '.join(command)}")
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise StepFailure(step, detail)


def _sqlite_db_path(db_url: str) -> Path:
    if not db_url.startswith("sqlite:///"):
        raise StepFailure("db-reset", f"unsupported CAPITAL_OS_DB_URL scheme for smoke reset: {db_url}")
    raw_path = db_url[len("sqlite:///") :]
    if raw_path.startswith("/"):
        db_path = Path(raw_path)
    else:
        db_path = ROOT / raw_path
    return db_path


def _reset_db(env: dict[str, str]) -> None:
    db_url = env["CAPITAL_OS_DB_URL"]
    db_path = _sqlite_db_path(db_url)
    if db_path.exists():
        db_path.unlink()
        print(f"[mvp-smoke] removed existing database: {db_path}")
    db_path.parent.mkdir(parents=True, exist_ok=True)


def _http_call(
    *,
    method: str,
    url: str,
    token: str | None = None,
    payload: dict | None = None,
    expected_status: int = 200,
    step: str,
) -> dict:
    headers = {"content-type": "application/json"}
    if token:
        headers["x-capital-auth-token"] = token
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, method=method, headers=headers, data=body)
    try:
        with request.urlopen(req, timeout=10) as resp:
            status = resp.getcode()
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        raise StepFailure(step, f"{method} {url} returned {exc.code}: {raw}") from exc
    except Exception as exc:
        raise StepFailure(step, f"{method} {url} failed: {exc}") from exc
    if status != expected_status:
        raise StepFailure(step, f"{method} {url} returned {status} (expected {expected_status})")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StepFailure(step, f"{method} {url} returned non-JSON response") from exc


def _assert(condition: bool, step: str, message: str) -> None:
    if not condition:
        raise StepFailure(step, message)


def _wait_for_health(base_url: str) -> None:
    step = "api-health"
    health_url = f"{base_url}/health"
    deadline = time.monotonic() + 12.0
    last_error: str | None = None
    while time.monotonic() < deadline:
        try:
            payload = _http_call(method="GET", url=health_url, expected_status=200, step=step)
            _assert(payload.get("status") == "ok", step, "health payload missing status=ok")
            return
        except StepFailure as exc:
            last_error = str(exc)
            time.sleep(0.2)
    raise StepFailure(step, last_error or "health endpoint did not become ready")


def _tool(base_url: str, token: str, tool_name: str, payload: dict, step: str) -> dict:
    url = f"{base_url}/tools/{tool_name}"
    return _http_call(method="POST", url=url, token=token, payload=payload, expected_status=200, step=step)


def run_smoke() -> None:
    env = _env()
    base_url = env["BASE_URL"].rstrip("/")
    token = env["CAPITAL_OS_AUTH_TOKEN"]

    _run_step("stop-runtime", ["make", "stop"], env)
    _reset_db(env)
    _run_step("migrate", ["python3", "scripts/apply_migrations.py"], env)
    _run_step("seed-coa", ["python3", "scripts/import_coa.py", "config/coa.yaml"], env)
    _run_step("start-runtime", ["make", "run"], env)

    try:
        _wait_for_health(base_url)

        list_accounts = _tool(
            base_url,
            token,
            "list_accounts",
            {"limit": 50, "correlation_id": "corr-smoke-read-accounts-1"},
            "read-list-accounts",
        )
        account_ids = {item["account_id"] for item in list_accounts.get("accounts", [])}
        _assert(SMOKE_ACCOUNT_ASSET in account_ids, "read-list-accounts", "seeded asset account missing")
        _assert(SMOKE_ACCOUNT_EQUITY in account_ids, "read-list-accounts", "seeded equity account missing")

        tx_payload = {
            "source_system": SMOKE_SOURCE_SYSTEM,
            "external_id": SMOKE_EXTERNAL_ID,
            "date": "2026-02-16T00:00:00Z",
            "description": "MVP smoke transaction",
            "postings": [
                {"account_id": SMOKE_ACCOUNT_ASSET, "amount": "125.0000", "currency": "USD"},
                {"account_id": SMOKE_ACCOUNT_EQUITY, "amount": "-125.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-smoke-write-tx-1",
        }
        tx_first = _tool(base_url, token, "record_transaction_bundle", tx_payload, "write-transaction-first")
        _assert(tx_first.get("status") == "committed", "write-transaction-first", "expected committed status")
        tx_id = tx_first.get("transaction_id")
        _assert(bool(tx_id), "write-transaction-first", "missing transaction_id")

        tx_replay_payload = dict(tx_payload)
        tx_replay_payload["correlation_id"] = "corr-smoke-write-tx-2"
        tx_replay = _tool(
            base_url,
            token,
            "record_transaction_bundle",
            tx_replay_payload,
            "write-transaction-idempotent",
        )
        _assert(
            tx_replay.get("status") == "idempotent-replay",
            "write-transaction-idempotent",
            "expected idempotent-replay status",
        )
        _assert(tx_replay.get("transaction_id") == tx_id, "write-transaction-idempotent", "transaction_id mismatch")

        snapshot = _tool(
            base_url,
            token,
            "record_balance_snapshot",
            {
                "source_system": SMOKE_SOURCE_SYSTEM,
                "account_id": SMOKE_ACCOUNT_ASSET,
                "snapshot_date": "2026-02-16",
                "balance": "123.4500",
                "currency": "USD",
                "source_artifact_id": "smoke-artifact-001",
                "correlation_id": "corr-smoke-write-snapshot-1",
            },
            "write-snapshot",
        )
        _assert(snapshot.get("status") == "recorded", "write-snapshot", "expected recorded status")

        obligation = _tool(
            base_url,
            token,
            "create_or_update_obligation",
            {
                "source_system": SMOKE_SOURCE_SYSTEM,
                "name": SMOKE_OBLIGATION_NAME,
                "account_id": SMOKE_ACCOUNT_EQUITY,
                "cadence": "monthly",
                "expected_amount": "25.0000",
                "variability_flag": False,
                "next_due_date": "2026-03-15",
                "metadata": {"kind": "smoke"},
                "correlation_id": "corr-smoke-write-obligation-1",
            },
            "write-obligation",
        )
        _assert(obligation.get("status") == "created", "write-obligation", "expected created status")

        listed_tx = _tool(
            base_url,
            token,
            "list_transactions",
            {"limit": 10, "correlation_id": "corr-smoke-read-list-tx-1"},
            "read-list-transactions",
        )
        tx_ids = {row["external_id"] for row in listed_tx.get("transactions", [])}
        _assert(SMOKE_EXTERNAL_ID in tx_ids, "read-list-transactions", "smoke transaction not found in list")

        tx_lookup = _tool(
            base_url,
            token,
            "get_transaction_by_external_id",
            {
                "source_system": SMOKE_SOURCE_SYSTEM,
                "external_id": SMOKE_EXTERNAL_ID,
                "correlation_id": "corr-smoke-read-get-tx-1",
            },
            "read-get-transaction",
        )
        looked_up_tx = tx_lookup.get("transaction") or {}
        _assert(looked_up_tx.get("transaction_id") == tx_id, "read-get-transaction", "lookup transaction mismatch")

        obligations = _tool(
            base_url,
            token,
            "list_obligations",
            {"limit": 50, "active_only": True, "correlation_id": "corr-smoke-read-list-obligations-1"},
            "read-list-obligations",
        )
        obligation_names = {row["name"] for row in obligations.get("obligations", [])}
        _assert(SMOKE_OBLIGATION_NAME in obligation_names, "read-list-obligations", "smoke obligation missing")

        balances = _tool(
            base_url,
            token,
            "get_account_balances",
            {
                "as_of_date": "2026-02-16",
                "source_policy": "best_available",
                "correlation_id": "corr-smoke-read-balances-1",
            },
            "read-get-balances",
        )
        rows = {row["account_id"]: row for row in balances.get("balances", [])}
        cash_row = rows.get(SMOKE_ACCOUNT_ASSET)
        _assert(cash_row is not None, "read-get-balances", "smoke asset balance missing")
        _assert(cash_row.get("source_used") == "snapshot", "read-get-balances", "expected snapshot source")
        _assert(str(cash_row.get("balance")) == "123.45", "read-get-balances", "unexpected balance value")

        listed_tx_repeat = _tool(
            base_url,
            token,
            "list_transactions",
            {"limit": 10, "correlation_id": "corr-smoke-read-list-tx-2"},
            "read-list-transactions-repeat",
        )
        _assert(
            listed_tx_repeat.get("transactions") == listed_tx.get("transactions"),
            "read-list-transactions-repeat",
            "list_transactions payload changed across identical state",
        )
        print("[mvp-smoke] SUCCESS: deterministic smoke flow completed")
    finally:
        _run_step("stop-runtime", ["make", "stop"], env)


def main() -> int:
    try:
        run_smoke()
        return 0
    except StepFailure as exc:
        print(f"[mvp-smoke] FAILURE in step '{exc.step}': {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
