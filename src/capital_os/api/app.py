from __future__ import annotations

from datetime import timezone, datetime
from time import perf_counter
import re

from fastapi import FastAPI, HTTPException, Request
from pydantic import ValidationError

from capital_os.db.session import transaction
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash
from capital_os.security import (
    authenticate_token,
    authorize_tool,
    clear_request_security_context,
    set_request_security_context,
)
from capital_os.security.context import RequestSecurityContext
from capital_os.tools import (
    approve_config_change,
    analyze_debt,
    approve_proposed_transaction,
    close_period,
    compute_consolidated_posture,
    compute_capital_posture,
    create_account,
    create_or_update_obligation,
    get_config,
    get_account_balances,
    get_account_tree,
    get_proposal,
    get_transaction_by_external_id,
    list_accounts,
    list_obligations,
    list_proposals,
    list_transactions,
    lock_period,
    propose_config_change,
    reconcile_account,
    record_balance_snapshot,
    record_transaction_bundle,
    reject_proposed_transaction,
    simulate_spend,
)

app = FastAPI(title="Capital OS")
CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
AUTH_TOKEN_HEADER = "x-capital-auth-token"
WRITE_TOOLS = {
    "create_account",
    "record_transaction_bundle",
    "record_balance_snapshot",
    "create_or_update_obligation",
    "approve_proposed_transaction",
    "reject_proposed_transaction",
    "propose_config_change",
    "approve_config_change",
    "close_period",
    "lock_period",
}

TOOL_HANDLERS = {
    "create_account": create_account.handle,
    "record_transaction_bundle": record_transaction_bundle.handle,
    "record_balance_snapshot": record_balance_snapshot.handle,
    "create_or_update_obligation": create_or_update_obligation.handle,
    "compute_capital_posture": compute_capital_posture.handle,
    "compute_consolidated_posture": compute_consolidated_posture.handle,
    "simulate_spend": simulate_spend.handle,
    "analyze_debt": analyze_debt.handle,
    "approve_proposed_transaction": approve_proposed_transaction.handle,
    "reject_proposed_transaction": reject_proposed_transaction.handle,
    "list_accounts": list_accounts.handle,
    "get_account_tree": get_account_tree.handle,
    "get_account_balances": get_account_balances.handle,
    "list_transactions": list_transactions.handle,
    "get_transaction_by_external_id": get_transaction_by_external_id.handle,
    "list_obligations": list_obligations.handle,
    "list_proposals": list_proposals.handle,
    "get_proposal": get_proposal.handle,
    "get_config": get_config.handle,
    "propose_config_change": propose_config_change.handle,
    "approve_config_change": approve_config_change.handle,
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


def _is_write_tool(tool_name: str) -> bool:
    return tool_name in WRITE_TOOLS


def _extract_correlation_id(payload: dict) -> str:
    raw_value = payload.get("correlation_id")
    if not isinstance(raw_value, str) or not CORRELATION_ID_PATTERN.match(raw_value):
        raise ValueError("correlation_id is required and must match ^[A-Za-z0-9._:-]{1,128}$")
    return raw_value


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
    fail_closed: bool = False,
) -> None:
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
    except Exception as exc:
        if fail_closed:
            raise HTTPException(status_code=500, detail={"error": "event_log_failure"}) from exc


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
    if not isinstance(payload, dict):
        payload = {}

    started = perf_counter()
    input_hash = payload_hash(payload)
    correlation_id = payload.get("correlation_id", "unknown")

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

    try:
        correlation_id = _extract_correlation_id(payload)
    except ValueError as exc:
        error_payload = {
            "error": "validation_error",
            "details": [
                {
                    "type": "value_error",
                    "loc": ["body", "correlation_id"],
                    "msg": str(exc),
                }
            ],
        }
        output_hash = payload_hash(error_payload)
        _emit_event(
            tool_name=tool_name,
            correlation_id="unknown",
            input_hash=input_hash,
            output_hash=output_hash,
            duration_ms=int((perf_counter() - started) * 1000),
            status="validation_error",
            error_code="validation_error",
            error_message="validation_error",
            actor_id=auth_context.actor_id,
            authn_method=auth_context.authn_method,
            authorization_result="denied",
            fail_closed=_is_write_tool(tool_name),
        )
        raise HTTPException(status_code=422, detail=error_payload) from exc

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

    context_token = set_request_security_context(
        RequestSecurityContext(
            actor_id=auth_context.actor_id,
            authn_method=auth_context.authn_method,
            authorization_result="allowed",
        )
    )
    try:
        result = handler(payload)
        return result.model_dump()
    except ValidationError as exc:
        error_payload = {"error": "validation_error", "details": _sanitize_validation_errors(exc.errors())}
        output_hash = payload_hash(error_payload)
        _emit_event(
            tool_name=tool_name,
            correlation_id=correlation_id,
            input_hash=input_hash,
            output_hash=output_hash,
            duration_ms=int((perf_counter() - started) * 1000),
            status="validation_error",
            error_code="validation_error",
            error_message="validation_error",
            fail_closed=True,
        )
        raise HTTPException(status_code=422, detail=error_payload) from exc
    except Exception as exc:
        error_payload = {"error": "tool_execution_error", "message": str(exc)}
        output_hash = payload_hash(error_payload)
        _emit_event(
            tool_name=tool_name,
            correlation_id=correlation_id,
            input_hash=input_hash,
            output_hash=output_hash,
            duration_ms=int((perf_counter() - started) * 1000),
            status="error",
            error_code="tool_execution_error",
            error_message="tool_execution_error",
            fail_closed=_is_write_tool(tool_name),
        )
        raise HTTPException(status_code=400, detail=error_payload) from exc
    finally:
        clear_request_security_context(context_token)
