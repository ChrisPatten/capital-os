from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from capital_os.domain.ledger.invariants import normalize_amount

_CONTENT_FIELDS = (
    "name",
    "direction",
    "amount",
    "cadence",
    "day_of_month",
    "anchor_date",
    "account_id",
    "bucket",
    "effective_date",
    "source",
    "metadata",
    "entity_id",
)

_ROW_COLUMNS = (
    "item_id, item_key, name, direction, amount, cadence, day_of_month, anchor_date, "
    "account_id, bucket, active, effective_date, source, metadata, entity_id"
)


def _row_to_dict(row) -> dict[str, Any]:
    return {
        "item_id": str(row["item_id"]),
        "item_key": row["item_key"],
        "name": row["name"],
        "direction": row["direction"],
        "amount": normalize_amount(row["amount"]),
        "cadence": row["cadence"],
        "day_of_month": row["day_of_month"],
        "anchor_date": row["anchor_date"],
        "account_id": row["account_id"],
        "bucket": row["bucket"],
        "active": bool(row["active"]),
        "effective_date": row["effective_date"],
        "source": row["source"],
        "metadata": json.loads(row["metadata"]),
        "entity_id": row["entity_id"],
    }


def account_exists(conn, account_id: str) -> bool:
    return conn.execute("SELECT 1 FROM accounts WHERE account_id=?", (account_id,)).fetchone() is not None


def fetch_active_version(conn, item_key: str) -> dict[str, Any] | None:
    row = conn.execute(
        f"SELECT {_ROW_COLUMNS} FROM budget_items WHERE item_key=? AND active=1", (item_key,)
    ).fetchone()
    return _row_to_dict(row) if row else None


def fetch_latest_version(conn, item_key: str) -> dict[str, Any] | None:
    row = conn.execute(
        f"SELECT {_ROW_COLUMNS} FROM budget_items WHERE item_key=? "
        "ORDER BY effective_date DESC, created_at DESC, rowid DESC LIMIT 1",
        (item_key,),
    ).fetchone()
    return _row_to_dict(row) if row else None


def normalized_content(payload: dict[str, Any]) -> dict[str, Any]:
    """Content fields of a payload or stored row in a directly comparable form."""
    return {
        "name": payload["name"],
        "direction": payload["direction"],
        "amount": normalize_amount(payload["amount"]),
        "cadence": payload["cadence"],
        "day_of_month": payload.get("day_of_month"),
        "anchor_date": str(payload["anchor_date"]) if payload.get("anchor_date") is not None else None,
        "account_id": payload.get("account_id"),
        "bucket": payload.get("bucket"),
        "effective_date": str(payload["effective_date"]),
        "source": payload.get("source"),
        "metadata": payload.get("metadata") or {},
        "entity_id": payload["entity_id"],
    }


def deactivate_item(conn, item_id: str) -> None:
    conn.execute(
        "UPDATE budget_items SET active=0, updated_at=CURRENT_TIMESTAMP WHERE item_id=?", (item_id,)
    )


def insert_item(conn, payload: dict[str, Any]) -> str:
    content = normalized_content(payload)
    item_id = str(uuid4())
    conn.execute(
        """
        INSERT INTO budget_items (
            item_id, item_key, name, direction, amount, cadence, day_of_month, anchor_date,
            account_id, bucket, active, effective_date, source, metadata, entity_id
        ) VALUES (?,?,?,?,?,?,?,?,?,?,1,?,?,?,?)
        """,
        (
            item_id,
            payload["item_key"],
            content["name"],
            content["direction"],
            str(content["amount"]),
            content["cadence"],
            content["day_of_month"],
            content["anchor_date"],
            content["account_id"],
            content["bucket"],
            content["effective_date"],
            content["source"],
            json.dumps(content["metadata"], separators=(",", ":"), sort_keys=True),
            content["entity_id"],
        ),
    )
    return item_id


def has_any_version(conn, item_key: str) -> bool:
    return conn.execute("SELECT 1 FROM budget_items WHERE item_key=? LIMIT 1", (item_key,)).fetchone() is not None


def list_items_page(
    conn,
    *,
    limit: int,
    cursor: dict[str, str] | None,
    active_only: bool,
    direction: str | None,
    bucket: str | None,
    account_id: str | None,
) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if cursor:
        where.append(
            "(item_key > ? OR (item_key = ? AND (effective_date > ? OR (effective_date = ? AND item_id > ?))))"
        )
        params.extend(
            [cursor["item_key"], cursor["item_key"], cursor["effective_date"], cursor["effective_date"], cursor["item_id"]]
        )
    if active_only:
        where.append("active = 1")
    if direction is not None:
        where.append("direction = ?")
        params.append(direction)
    if bucket is not None:
        where.append("bucket = ?")
        params.append(bucket)
    if account_id is not None:
        where.append("account_id = ?")
        params.append(account_id)
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    params.append(limit + 1)
    rows = conn.execute(
        f"""
        SELECT {_ROW_COLUMNS} FROM budget_items
        {where_clause}
        ORDER BY item_key ASC, effective_date ASC, item_id ASC
        LIMIT ?
        """,
        tuple(params),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def fetch_summary_rows(conn, *, entity_id: str | None, as_of_date: str | None) -> list[dict[str, Any]]:
    where = ["active = 1"]
    params: list[Any] = []
    if entity_id is not None:
        where.append("entity_id = ?")
        params.append(entity_id)
    if as_of_date is not None:
        where.append("effective_date <= ?")
        params.append(as_of_date)
    rows = conn.execute(
        f"SELECT {_ROW_COLUMNS} FROM budget_items WHERE {' AND '.join(where)} ORDER BY item_key, item_id",
        tuple(params),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]

