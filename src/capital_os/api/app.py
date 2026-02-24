from __future__ import annotations

from datetime import timezone, datetime
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request

from capital_os.db.session import transaction
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash
from capital_os.runtime.execute_tool import TOOL_HANDLERS, execute_tool
from capital_os.security import (
    authenticate_token,
    authorize_tool,
)

app = FastAPI(title="Capital OS")
AUTH_TOKEN_HEADER = "x-capital-auth-token"

# HTTP status code mapping from ToolResult.status
_STATUS_CODE_MAP = {
    "unknown_tool": 404,
    "validation_error": 422,
    "error": 400,
    "event_log_failure": 500,
}


def _emit_event(
    *,
    tool_name: str,
    correlation_id: str,
    input_hash: str,
    output_hash: str,
    duration_ms: int,
    status: str,
    error_code: str | None = None,
    error_message: str | None = None,
    actor_id: str | None = None,
    authn_method: str | None = None,
    authorization_result: str | None = None,
    violation_code: str | None = None,
) -> None:
    """Log an event for auth/authz failures (never fail-closed)."""
    try:
        with transaction() as conn:
            log_event(
                conn,
                tool_name=tool_name,
                correlation_id=correlation_id,
                input_hash=input_hash,
                output_hash=output_hash,
                duration_ms=duration_ms,
                status=status,
                error_code=error_code,
                error_message=error_message,
                actor_id=actor_id,
                authn_method=authn_method,
                authorization_result=authorization_result,
                violation_code=violation_code,
            )
    except Exception:
        pass


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
    # Early unknown-tool check (before auth, preserving existing behaviour)
    if tool_name not in TOOL_HANDLERS:
        raise HTTPException(status_code=404, detail={"error": "unknown_tool", "tool": tool_name})

    payload = await request.json()
    if not isinstance(payload, dict):
        payload = {}

    started = perf_counter()
    input_hash = payload_hash(payload)
    correlation_id = payload.get("correlation_id", "unknown")

    # --- 1. Authenticate ---
    auth_context = authenticate_token(request.headers.get(AUTH_TOKEN_HEADER))
    if auth_context is None:
        error_payload = {"error": "authentication_required"}
        output_hash = payload_hash(error_payload)
        _emit_event(
            tool_name=tool_name,
            correlation_id=correlation_id if isinstance(correlation_id, str) else "unknown",
            input_hash=input_hash,
            output_hash=output_hash,
            duration_ms=int((perf_counter() - started) * 1000),
            status="auth_error",
            error_code="authentication_required",
            error_message="authentication_required",
            authorization_result="denied",
        )
        raise HTTPException(status_code=401, detail=error_payload)

    # --- 2. Authorize ---
    if not authorize_tool(auth_context, tool_name):
        error_payload = {"error": "forbidden"}
        output_hash = payload_hash(error_payload)
        _emit_event(
            tool_name=tool_name,
            correlation_id=correlation_id,
            input_hash=input_hash,
            output_hash=output_hash,
            duration_ms=int((perf_counter() - started) * 1000),
            status="authz_denied",
            error_code="forbidden",
            error_message="forbidden",
            actor_id=auth_context.actor_id,
            authn_method=auth_context.authn_method,
            authorization_result="denied",
        )
        raise HTTPException(status_code=403, detail=error_payload)

    # --- 3. Delegate to shared runtime executor ---
    result = execute_tool(
        tool_name,
        payload,
        actor_id=auth_context.actor_id,
        authn_method=auth_context.authn_method,
        authorization_result="allowed",
    )

    # --- 4. Map ToolResult to HTTP response ---
    if result.success:
        return result.payload

    status_code = _STATUS_CODE_MAP.get(result.status, 400)
    raise HTTPException(status_code=status_code, detail=result.payload)
