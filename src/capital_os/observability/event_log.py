from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from capital_os.security.context import get_request_security_context


def log_event(
    conn,
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
    request_context = get_request_security_context()
    effective_actor_id = actor_id if actor_id is not None else (
        request_context.actor_id if request_context else None
    )
    effective_authn_method = authn_method if authn_method is not None else (
        request_context.authn_method if request_context else None
    )
    effective_authorization_result = (
        authorization_result
        if authorization_result is not None
        else (request_context.authorization_result if request_context else None)
    )

    conn.execute(
        """
        INSERT INTO event_log (
            event_id, tool_name, correlation_id, input_hash, output_hash,
            event_timestamp, duration_ms, status, error_code, error_message,
            actor_id, authn_method, authorization_result, violation_code
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            str(uuid4()),
            tool_name,
            correlation_id,
            input_hash,
            output_hash,
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            duration_ms,
            status,
            error_code,
            error_message,
            effective_actor_id,
            effective_authn_method,
            effective_authorization_result,
            violation_code,
        ),
    )
