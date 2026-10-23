from __future__ import annotations

from typing import Any

from capital_os.domain.ledger.invariants import normalize_amount


def account_exists(conn, account_id: str) -> bool:
    return conn.execute("SELECT 1 FROM accounts WHERE account_id=?", (account_id,)).fetchone() is not None


def fetch_latest_snapshot(conn, *, account_id: str, entity_id: str, on_or_before: str) -> dict[str, Any] | None:
    """Latest snapshot for the account whose DATE part is <= on_or_before.

    snapshot_date is free TEXT (date or datetime); only the first 10 chars are compared.
    Ties on the date part break by full snapshot_date text, then snapshot_id (descending).
    """
    row = conn.execute(
        """
        SELECT snapshot_id, substr(snapshot_date, 1, 10) AS snap_day, balance
        FROM balance_snapshots
        WHERE account_id = ? AND entity_id = ? AND substr(snapshot_date, 1, 10) <= ?
        ORDER BY snap_day DESC, snapshot_date DESC, snapshot_id DESC
        LIMIT 1
        """,
        (account_id, entity_id, on_or_before),
    ).fetchone()
    if row is None:
        return None
    return {"snapshot_date": row["snap_day"], "balance": normalize_amount(row["balance"])}


def fetch_budget_items(conn, *, account_id: str, entity_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT item_id, name, direction, amount, cadence, day_of_month, anchor_date, effective_date
        FROM budget_items
        WHERE active = 1 AND account_id = ? AND entity_id = ?
        ORDER BY item_key, item_id
        """,
        (account_id, entity_id),
    ).fetchall()
    return [
        {
            "item_id": str(r["item_id"]),
            "name": r["name"],
            "direction": r["direction"],
            "amount": normalize_amount(r["amount"]),
            "cadence": r["cadence"],
            "day_of_month": r["day_of_month"],
            "anchor_date": r["anchor_date"],
            "effective_date": r["effective_date"],
        }
        for r in rows
    ]


def fetch_one_time_obligations(conn, *, account_id: str, entity_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT obligation_id, name, expected_amount, next_due_date
        FROM obligations
        WHERE active = 1 AND funding_account_id = ? AND entity_id = ?
          AND (recurrence IS NULL OR recurrence = 'one_time')
        ORDER BY obligation_id
        """,
        (account_id, entity_id),
    ).fetchall()
    return [
        {
            "obligation_id": str(r["obligation_id"]),
            "name": r["name"],
            "amount": normalize_amount(r["expected_amount"]),
            "next_due_date": str(r["next_due_date"])[:10],
        }
        for r in rows
    ]
