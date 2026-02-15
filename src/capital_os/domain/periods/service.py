from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from capital_os.domain.entities import DEFAULT_ENTITY_ID
from capital_os.domain.ledger.invariants import InvariantError
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash


def _period_key_for_tx_date(tx_date: str) -> str:
    normalized = tx_date.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    parsed = parsed.astimezone(timezone.utc)
    return parsed.strftime("%Y-%m")


def _fetch_period(conn, *, period_key: str, entity_id: str) -> dict | None:
    row = conn.execute(
        """
        SELECT period_id, period_key, entity_id, status, actor_id, correlation_id, closed_at, locked_at
        FROM accounting_periods
        WHERE period_key=? AND entity_id=?
        """,
        (period_key, entity_id),
    ).fetchone()
    return dict(row) if row else None


def _upsert_period_status(
    conn,
    *,
    period_key: str,
    entity_id: str,
    status: str,
    actor_id: str | None,
    correlation_id: str,
) -> dict:
    row = _fetch_period(conn, period_key=period_key, entity_id=entity_id)
    now = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    if not row:
        period_id = str(uuid4())
        closed_at = now if status in {"closed", "locked"} else None
        locked_at = now if status == "locked" else None
        conn.execute(
            """
            INSERT INTO accounting_periods (
              period_id, period_key, entity_id, status, actor_id, correlation_id, closed_at, locked_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (period_id, period_key, entity_id, status, actor_id, correlation_id, closed_at, locked_at),
        )
        row = _fetch_period(conn, period_key=period_key, entity_id=entity_id)
        if not row:
            raise InvariantError("failed to persist accounting period")
        row["result"] = status
        return row

    if row["status"] == "locked":
        row["result"] = "already_locked"
        return row

    if status == "closed" and row["status"] == "closed":
        row["result"] = "already_closed"
        return row

    closed_at = row["closed_at"] or now
    locked_at = row["locked_at"]
    if status == "locked":
        locked_at = now

    conn.execute(
        """
        UPDATE accounting_periods
        SET status=?, actor_id=?, correlation_id=?, closed_at=?, locked_at=?
        WHERE period_id=?
        """,
        (status, actor_id, correlation_id, closed_at, locked_at, row["period_id"]),
    )

    updated = _fetch_period(conn, period_key=period_key, entity_id=entity_id)
    if not updated:
        raise InvariantError("failed to update accounting period")
    updated["result"] = status
    return updated


def enforce_period_write_constraints(conn, payload: dict) -> bool:
    period_key = _period_key_for_tx_date(str(payload["date"]))
    entity_id = payload.get("entity_id", DEFAULT_ENTITY_ID)
    row = _fetch_period(conn, period_key=period_key, entity_id=entity_id)
    if not row:
        return False

    status = row["status"]
    if status == "open":
        return False

    if status == "closed":
        if not payload.get("is_adjusting_entry"):
            raise InvariantError("period_closed_requires_adjusting_entry")
        return True

    if status == "locked":
        if not payload.get("override_period_lock"):
            raise InvariantError("period_locked")
        return True

    raise InvariantError(f"unsupported period status: {status}")


def close_period(conn, payload: dict) -> dict:
    started = perf_counter()
    input_hash = payload_hash(payload)
    entity_id = payload.get("entity_id", DEFAULT_ENTITY_ID)
    row = _upsert_period_status(
        conn,
        period_key=payload["period_key"],
        entity_id=entity_id,
        status="closed",
        actor_id=payload.get("actor_id"),
        correlation_id=payload["correlation_id"],
    )
    response = {
        "status": row["result"],
        "period_key": row["period_key"],
        "entity_id": row["entity_id"],
        "state": row["status"],
        "closed_at": row["closed_at"],
        "locked_at": row["locked_at"],
        "correlation_id": payload["correlation_id"],
    }
    output_hash = payload_hash(response)
    response["output_hash"] = output_hash
    log_event(
        conn,
        tool_name="close_period",
        correlation_id=payload["correlation_id"],
        input_hash=input_hash,
        output_hash=output_hash,
        duration_ms=int((perf_counter() - started) * 1000),
        status="ok",
    )
    return response


def lock_period(conn, payload: dict) -> dict:
    started = perf_counter()
    input_hash = payload_hash(payload)
    entity_id = payload.get("entity_id", DEFAULT_ENTITY_ID)
    row = _upsert_period_status(
        conn,
        period_key=payload["period_key"],
        entity_id=entity_id,
        status="locked",
        actor_id=payload.get("actor_id"),
        correlation_id=payload["correlation_id"],
    )
    response = {
        "status": row["result"],
        "period_key": row["period_key"],
        "entity_id": row["entity_id"],
        "state": row["status"],
        "closed_at": row["closed_at"],
        "locked_at": row["locked_at"],
        "correlation_id": payload["correlation_id"],
    }
    output_hash = payload_hash(response)
    response["output_hash"] = output_hash
    log_event(
        conn,
        tool_name="lock_period",
        correlation_id=payload["correlation_id"],
        input_hash=input_hash,
        output_hash=output_hash,
        duration_ms=int((perf_counter() - started) * 1000),
        status="ok",
    )
    return response
