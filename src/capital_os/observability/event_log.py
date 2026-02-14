from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


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
) -> None:
    conn.execute(
        """
        INSERT INTO event_log (
            event_id, tool_name, correlation_id, input_hash, output_hash,
            event_timestamp, duration_ms, status, error_code, error_message
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
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
        ),
    )
