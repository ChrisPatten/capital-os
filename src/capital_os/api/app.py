from __future__ import annotations

from datetime import timezone, datetime
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from pydantic import ValidationError

from capital_os.db.session import transaction
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash
from capital_os.tools import (
    compute_capital_posture,
    create_or_update_obligation,
    record_balance_snapshot,
    record_transaction_bundle,
    simulate_spend,
)

app = FastAPI(title="Capital OS")

TOOL_HANDLERS = {
    "record_transaction_bundle": record_transaction_bundle.handle,
    "record_balance_snapshot": record_balance_snapshot.handle,
    "create_or_update_obligation": create_or_update_obligation.handle,
    "compute_capital_posture": compute_capital_posture.handle,
    "simulate_spend": simulate_spend.handle,
}


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
        error_payload = {"error": "validation_error", "details": exc.errors()}
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
                    error_message=str(exc),
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
                    error_message=str(exc),
                )
        except Exception:
            # Fail-closed for write tools when logging fails.
            pass
        raise HTTPException(status_code=400, detail=error_payload) from exc
