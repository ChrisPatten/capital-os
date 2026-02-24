"""Shared tool execution runtime for HTTP and CLI adapters.

This module provides the canonical execution path for all Capital OS tools.
Both the HTTP (FastAPI) and CLI (Typer) adapters delegate to ``execute_tool``
after their transport-specific concerns (auth for HTTP, argument parsing for
CLI) are resolved.

Invariants preserved through this path:
- Schema validation (Pydantic)
- Deterministic input/output hashing
- Event logging with fail-closed write semantics
- DB transaction boundaries
- Append-only and balanced-posting protections
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from time import perf_counter

from pydantic import ValidationError

from capital_os.db.session import transaction
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash
from capital_os.security.context import (
    RequestSecurityContext,
    clear_request_security_context,
    set_request_security_context,
)
from capital_os.tools import (
    analyze_debt,
    approve_config_change,
    approve_proposed_transaction,
    close_period,
    compute_capital_posture,
    compute_consolidated_posture,
    create_account,
    create_or_update_obligation,
    get_account_balances,
    get_account_tree,
    get_config,
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
    update_account_metadata,
)

CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

WRITE_TOOLS = {
    "create_account",
    "update_account_metadata",
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
    "update_account_metadata": update_account_metadata.handle,
    "close_period": close_period.handle,
    "lock_period": lock_period.handle,
}


@dataclass(frozen=True)
class ToolResult:
    """Transport-agnostic result envelope from tool execution."""

    success: bool
    payload: dict
    status: str  # "ok", "unknown_tool", "validation_error", "error", "event_log_failure"


def tool_names() -> list[str]:
    """Return sorted list of registered tool names."""
    return sorted(TOOL_HANDLERS)


def _is_write_tool(tool_name: str) -> bool:
    return tool_name in WRITE_TOOLS


def _extract_correlation_id(payload: dict) -> str:
    raw_value = payload.get("correlation_id")
    if not isinstance(raw_value, str) or not CORRELATION_ID_PATTERN.match(raw_value):
        raise ValueError(
            "correlation_id is required and must match ^[A-Za-z0-9._:-]{1,128}$"
        )
    return raw_value


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
                str(k): _safe_ctx_value(v)
                for k, v in entry["ctx"].items()
                if k != "input"
            }
        sanitized.append(entry)
    return sanitized


def _try_log_event(*, fail_closed: bool, **kwargs) -> bool:
    """Persist an event log entry.

    Returns True on success or non-fatal failure.
    Returns False when *fail_closed* is True and logging fails.
    """
    try:
        with transaction() as conn:
            log_event(conn, **kwargs)
        return True
    except Exception:
        return not fail_closed


def execute_tool(
    tool_name: str,
    payload: dict,
    *,
    actor_id: str,
    authn_method: str,
    authorization_result: str,
) -> ToolResult:
    """Shared tool execution entrypoint for HTTP and CLI adapters.

    Auth/authz is the caller's responsibility.  This function handles:
    - Tool lookup and dispatch
    - Correlation ID validation
    - Security context injection (ContextVar)
    - Pydantic schema validation error handling
    - Event logging for tool-level errors
    - Fail-closed write semantics
    """
    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        return ToolResult(
            success=False,
            payload={"error": "unknown_tool", "tool": tool_name},
            status="unknown_tool",
        )

    started = perf_counter()
    input_hash = payload_hash(payload)
    correlation_id = payload.get("correlation_id", "unknown")

    # --- Correlation ID validation ---
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
        logged = _try_log_event(
            fail_closed=_is_write_tool(tool_name),
            tool_name=tool_name,
            correlation_id="unknown",
            input_hash=input_hash,
            output_hash=output_hash,
            duration_ms=int((perf_counter() - started) * 1000),
            status="validation_error",
            error_code="validation_error",
            error_message="validation_error",
            actor_id=actor_id,
            authn_method=authn_method,
            authorization_result="denied",
        )
        if not logged:
            return ToolResult(
                success=False,
                payload={"error": "event_log_failure"},
                status="event_log_failure",
            )
        return ToolResult(
            success=False,
            payload=error_payload,
            status="validation_error",
        )

    # --- Set security context for duration of tool execution ---
    context_token = set_request_security_context(
        RequestSecurityContext(
            actor_id=actor_id,
            authn_method=authn_method,
            authorization_result=authorization_result,
        )
    )
    try:
        result = handler(payload)
        return ToolResult(
            success=True,
            payload=result.model_dump(),
            status="ok",
        )
    except ValidationError as exc:
        error_payload = {
            "error": "validation_error",
            "details": _sanitize_validation_errors(exc.errors()),
        }
        output_hash = payload_hash(error_payload)
        logged = _try_log_event(
            fail_closed=_is_write_tool(tool_name),
            tool_name=tool_name,
            correlation_id=correlation_id,
            input_hash=input_hash,
            output_hash=output_hash,
            duration_ms=int((perf_counter() - started) * 1000),
            status="validation_error",
            error_code="validation_error",
            error_message="validation_error",
            actor_id=actor_id,
            authn_method=authn_method,
            authorization_result=authorization_result,
        )
        if not logged:
            return ToolResult(
                success=False,
                payload={"error": "event_log_failure"},
                status="event_log_failure",
            )
        return ToolResult(
            success=False,
            payload=error_payload,
            status="validation_error",
        )
    except Exception as exc:
        error_payload = {"error": "tool_execution_error", "message": str(exc)}
        output_hash = payload_hash(error_payload)
        logged = _try_log_event(
            fail_closed=_is_write_tool(tool_name),
            tool_name=tool_name,
            correlation_id=correlation_id,
            input_hash=input_hash,
            output_hash=output_hash,
            duration_ms=int((perf_counter() - started) * 1000),
            status="error",
            error_code="tool_execution_error",
            error_message="tool_execution_error",
            actor_id=actor_id,
            authn_method=authn_method,
            authorization_result=authorization_result,
        )
        if not logged:
            return ToolResult(
                success=False,
                payload={"error": "event_log_failure"},
                status="event_log_failure",
            )
        return ToolResult(
            success=False,
            payload=error_payload,
            status="error",
        )
    finally:
        clear_request_security_context(context_token)
