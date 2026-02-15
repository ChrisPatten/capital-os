from __future__ import annotations

from datetime import timezone, datetime
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from pydantic import ValidationError

from capital_os.db.session import transaction
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash
from capital_os.tools import (
    analyze_debt,
    approve_proposed_transaction,
    close_period,
    compute_capital_posture,
    create_or_update_obligation,
    get_account_balances,
    get_account_tree,
    list_accounts,
    lock_period,
    reconcile_account,
    record_balance_snapshot,
    record_transaction_bundle,
    reject_proposed_transaction,
    simulate_spend,
)

app = FastAPI(title="Capital OS")

TOOL_HANDLERS = {
    "record_transaction_bundle": record_transaction_bundle.handle,
    "record_balance_snapshot": record_balance_snapshot.handle,
    "create_or_update_obligation": create_or_update_obligation.handle,
    "compute_capital_posture": compute_capital_posture.handle,
    "simulate_spend": simulate_spend.handle,
    "analyze_debt": analyze_debt.handle,
    "approve_proposed_transaction": approve_proposed_transaction.handle,
    "reject_proposed_transaction": reject_proposed_transaction.handle,
    "list_accounts": list_accounts.handle,
    "get_account_tree": get_account_tree.handle,
    "get_account_balances": get_account_balances.handle,
    "reconcile_account": reconcile_account.handle,
    "close_period": close_period.handle,
    "lock_period": lock_period.handle,
}


def _sanitize_validation_errors(errors: list[dict]) -> list[dict]:
    def _safe_ctx_value(value):
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, list):
            return [_safe_ctx_value(item) for item in value]
        if isinstance(value, dict):
            return {str(k): _safe_ctx_value(v) for k, v in value.items()}
        return str(value)

    sanitized: list[dict] = []
    for error in errors:
        entry = {key: value for key, value in error.items() if key != "input"}
        if "ctx" in entry and isinstance(entry["ctx"], dict):
            entry["ctx"] = {
                str(k): _safe_ctx_value(v) for k, v in entry["ctx"].items() if k != "input"
            }
        sanitized.append(entry)
    return sanitized


@app.get("/health")
def health() -> dict:
    try:
        with transaction() as conn:
            conn.execute("SELECT 1 AS ok").fetchone()
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"status": "down", "error": str(exc)}) from exc
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/tools/{tool_name}")
async def run_tool(tool_name: str, request: Request):
    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        raise HTTPException(status_code=404, detail={"error": "unknown_tool", "tool": tool_name})

    payload = await request.json()
    started = perf_counter()
    input_hash = payload_hash(payload)
    correlation_id = payload.get("correlation_id", "unknown")

    try:
        result = handler(payload)
        return result.model_dump()
    except ValidationError as exc:
        error_payload = {"error": "validation_error", "details": _sanitize_validation_errors(exc.errors())}
        output_hash = payload_hash(error_payload)
        try:
            with transaction() as conn:
                log_event(
                    conn,
                    tool_name=tool_name,
                    correlation_id=correlation_id,
                    input_hash=input_hash,
                    output_hash=output_hash,
                    duration_ms=int((perf_counter() - started) * 1000),
                    status="validation_error",
                    error_code="validation_error",
                    error_message="validation_error",
                )
        except Exception:
            raise HTTPException(status_code=500, detail={"error": "event_log_failure"}) from exc
        raise HTTPException(status_code=422, detail=error_payload) from exc
    except Exception as exc:
        error_payload = {"error": "tool_execution_error", "message": str(exc)}
        output_hash = payload_hash(error_payload)
        try:
            with transaction() as conn:
                log_event(
                    conn,
                    tool_name=tool_name,
                    correlation_id=correlation_id,
                    input_hash=input_hash,
                    output_hash=output_hash,
                    duration_ms=int((perf_counter() - started) * 1000),
                    status="error",
                    error_code="tool_execution_error",
                    error_message="tool_execution_error",
                )
        except Exception:
            # Fail-closed for write tools when logging fails.
            pass
        raise HTTPException(status_code=400, detail=error_payload) from exc
