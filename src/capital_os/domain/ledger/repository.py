from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from capital_os.domain.ledger.invariants import normalize_amount


def fetch_transaction_by_external_id(conn, source_system: str, external_id: str) -> dict | None:
    row = conn.execute(
        """
        SELECT transaction_id, response_payload
        FROM ledger_transactions
        WHERE source_system=? AND external_id=?
        """,
        (source_system, external_id),
    ).fetchone()
    if not row:
        return None
    response_payload = row["response_payload"]
    if response_payload:
        response_payload = json.loads(response_payload)
    return {"transaction_id": str(row["transaction_id"]), "response_payload": response_payload}


def insert_transaction_bundle(conn, payload: dict[str, Any]) -> tuple[str, list[str]]:
    postings = sorted(payload["postings"], key=lambda p: (p["account_id"], str(p["amount"]), p.get("memo") or ""))
    tx_id = str(uuid4())
    conn.execute(
        """
        INSERT INTO ledger_transactions (
            transaction_id, source_system, external_id, transaction_date, description, correlation_id, input_hash
        ) VALUES (?,?,?,?,?,?,?)
        """,
        (
            tx_id,
            payload["source_system"],
            payload["external_id"],
            payload["date"],
            payload["description"],
            payload["correlation_id"],
            payload["input_hash"],
        ),
    )
    posting_ids: list[str] = []
    for p in postings:
        posting_id = str(uuid4())
        conn.execute(
            """
            INSERT INTO ledger_postings (posting_id, transaction_id, account_id, amount, currency, memo)
            VALUES (?,?,?,?,?,?)
            """,
            (
                posting_id,
                tx_id,
                p["account_id"],
                str(normalize_amount(p["amount"])),
                p["currency"],
                p.get("memo"),
            ),
        )
        posting_ids.append(posting_id)

    return tx_id, posting_ids


def save_transaction_response(conn, transaction_id: str, response: dict, output_hash: str) -> None:
    conn.execute(
        """
        UPDATE ledger_transactions
        SET response_payload=?, output_hash=?
        WHERE transaction_id=?
        """,
        (json.dumps(response, separators=(",", ":")), output_hash, transaction_id),
    )


def upsert_balance_snapshot(conn, payload: dict[str, Any]) -> tuple[str, str]:
    existing = conn.execute(
        "SELECT snapshot_id FROM balance_snapshots WHERE account_id=? AND snapshot_date=?",
        (payload["account_id"], str(payload["snapshot_date"])),
    ).fetchone()
    if existing:
        snapshot_id = str(existing["snapshot_id"])
        conn.execute(
            """
            UPDATE balance_snapshots
            SET balance=?, currency=?, source_artifact_id=?, source_system=?, updated_at=CURRENT_TIMESTAMP
            WHERE snapshot_id=?
            """,
            (
                str(normalize_amount(payload["balance"])),
                payload["currency"],
                payload.get("source_artifact_id"),
                payload["source_system"],
                snapshot_id,
            ),
        )
        return snapshot_id, "updated"

    snapshot_id = str(uuid4())
    conn.execute(
        """
        INSERT INTO balance_snapshots (
            snapshot_id, source_system, account_id, snapshot_date, balance, currency, source_artifact_id
        ) VALUES (?,?,?,?,?,?,?)
        """,
        (
            snapshot_id,
            payload["source_system"],
            payload["account_id"],
            str(payload["snapshot_date"]),
            str(normalize_amount(payload["balance"])),
            payload["currency"],
            payload.get("source_artifact_id"),
        ),
    )
    return snapshot_id, "recorded"


def upsert_obligation(conn, payload: dict[str, Any]) -> tuple[str, str]:
    existing = conn.execute(
        "SELECT obligation_id FROM obligations WHERE source_system=? AND name=? AND account_id=?",
        (payload["source_system"], payload["name"], payload["account_id"]),
    ).fetchone()
    if existing:
        obligation_id = str(existing["obligation_id"])
        conn.execute(
            """
            UPDATE obligations
            SET cadence=?, expected_amount=?, variability_flag=?, next_due_date=?, metadata=?, active=1, updated_at=CURRENT_TIMESTAMP
            WHERE obligation_id=?
            """,
            (
                payload["cadence"],
                str(normalize_amount(payload["expected_amount"])),
                1 if payload.get("variability_flag", False) else 0,
                str(payload["next_due_date"]),
                json.dumps(payload.get("metadata", {}), separators=(",", ":")),
                obligation_id,
            ),
        )
        return obligation_id, "updated"

    obligation_id = str(uuid4())
    conn.execute(
        """
        INSERT INTO obligations (
            obligation_id, source_system, name, account_id, cadence, expected_amount,
            variability_flag, next_due_date, metadata, active
        ) VALUES (?,?,?,?,?,?,?,?,?,1)
        """,
        (
            obligation_id,
            payload["source_system"],
            payload["name"],
            payload["account_id"],
            payload["cadence"],
            str(normalize_amount(payload["expected_amount"])),
            1 if payload.get("variability_flag", False) else 0,
            str(payload["next_due_date"]),
            json.dumps(payload.get("metadata", {}), separators=(",", ":")),
        ),
    )
    return obligation_id, "created"


def create_account(conn, payload: dict[str, Any]) -> str:
    account_id = str(uuid4())
    conn.execute(
        """
        INSERT INTO accounts (account_id, code, name, account_type, parent_account_id, metadata)
        VALUES (?,?,?,?,?,?)
        """,
        (
            account_id,
            payload["code"],
            payload["name"],
            payload["account_type"],
            payload.get("parent_account_id"),
            json.dumps(payload.get("metadata", {}), separators=(",", ":")),
        ),
    )
    return account_id


def list_accounts_subtree(conn, root_account_id: str | None = None) -> list[dict[str, Any]]:
    if root_account_id:
        rows = conn.execute(
            """
            WITH RECURSIVE subtree AS (
                SELECT a.*, 0 AS depth FROM accounts a WHERE a.account_id=?
                UNION ALL
                SELECT c.*, s.depth + 1
                FROM accounts c
                JOIN subtree s ON c.parent_account_id = s.account_id
            )
            SELECT account_id, code, name, account_type, parent_account_id, metadata, depth
            FROM subtree
            ORDER BY depth, code, account_id
            """,
            (root_account_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT account_id, code, name, account_type, parent_account_id, metadata, 0 AS depth
            FROM accounts
            ORDER BY code, account_id
            """
        ).fetchall()

    result: list[dict[str, Any]] = []
    for row in rows:
        entry = dict(row)
        if entry.get("metadata"):
            entry["metadata"] = json.loads(entry["metadata"])
        result.append(entry)
    return result


def fetch_accounts_for_ids(conn, account_ids: list[str]) -> list[dict[str, Any]]:
    if not account_ids:
        return []

    placeholders = ",".join("?" for _ in account_ids)
    rows = conn.execute(
        f"""
        SELECT account_id, code, name, account_type
        FROM accounts
        WHERE account_id IN ({placeholders})
        ORDER BY code, account_id
        """,
        tuple(account_ids),
    ).fetchall()
    return [dict(row) for row in rows]


def list_accounts_page(conn, *, limit: int, cursor: dict[str, str] | None) -> list[dict[str, Any]]:
    params: tuple[Any, ...]
    where_clause = ""
    if cursor:
        where_clause = "WHERE (code > ? OR (code = ? AND account_id > ?))"
        params = (cursor["code"], cursor["code"], cursor["account_id"], limit + 1)
    else:
        params = (limit + 1,)

    rows = conn.execute(
        f"""
        SELECT account_id, code, name, account_type, parent_account_id, metadata
        FROM accounts
        {where_clause}
        ORDER BY code, account_id
        LIMIT ?
        """,
        params,
    ).fetchall()

    result: list[dict[str, Any]] = []
    for row in rows:
        entry = dict(row)
        entry["metadata"] = json.loads(entry["metadata"]) if entry.get("metadata") else {}
        result.append(entry)
    return result


def fetch_account_tree_rows(conn, root_account_id: str | None) -> list[dict[str, Any]]:
    if root_account_id:
        rows = conn.execute(
            """
            WITH RECURSIVE subtree AS (
                SELECT account_id, code, name, account_type, parent_account_id, metadata
                FROM accounts
                WHERE account_id = ?
                UNION ALL
                SELECT c.account_id, c.code, c.name, c.account_type, c.parent_account_id, c.metadata
                FROM accounts c
                JOIN subtree s ON c.parent_account_id = s.account_id
            )
            SELECT account_id, code, name, account_type, parent_account_id, metadata
            FROM subtree
            ORDER BY code, account_id
            """,
            (root_account_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT account_id, code, name, account_type, parent_account_id, metadata
            FROM accounts
            ORDER BY code, account_id
            """
        ).fetchall()

    result: list[dict[str, Any]] = []
    for row in rows:
        entry = dict(row)
        entry["metadata"] = json.loads(entry["metadata"]) if entry.get("metadata") else {}
        result.append(entry)
    return result


def fetch_account_balances_as_of(
    conn, *, as_of_date: str, source_policy: str
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        WITH ledger_totals AS (
            SELECT p.account_id, COALESCE(SUM(p.amount), 0) AS ledger_balance
            FROM ledger_postings p
            JOIN ledger_transactions t ON t.transaction_id = p.transaction_id
            WHERE date(t.transaction_date) <= date(?)
            GROUP BY p.account_id
        ),
        snapshots_ranked AS (
            SELECT
              s.account_id,
              s.balance,
              s.snapshot_date,
              ROW_NUMBER() OVER (
                PARTITION BY s.account_id
                ORDER BY s.snapshot_date DESC, s.snapshot_id DESC
              ) AS rn
            FROM balance_snapshots s
            WHERE date(s.snapshot_date) <= date(?)
        ),
        latest_snapshots AS (
            SELECT account_id, balance AS snapshot_balance, snapshot_date
            FROM snapshots_ranked
            WHERE rn = 1
        )
        SELECT
          a.account_id,
          a.code,
          a.name,
          a.account_type,
          COALESCE(lt.ledger_balance, 0) AS ledger_balance,
          ls.snapshot_balance,
          ls.snapshot_date
        FROM accounts a
        LEFT JOIN ledger_totals lt ON lt.account_id = a.account_id
        LEFT JOIN latest_snapshots ls ON ls.account_id = a.account_id
        ORDER BY a.code, a.account_id
        """,
        (as_of_date, as_of_date),
    ).fetchall()

    result: list[dict[str, Any]] = []
    for row in rows:
        entry = dict(row)
        ledger_balance = normalize_amount(entry["ledger_balance"])
        snapshot_balance = (
            normalize_amount(entry["snapshot_balance"]) if entry["snapshot_balance"] is not None else None
        )

        if source_policy == "ledger_only":
            balance = ledger_balance
            source_used = "ledger"
        elif source_policy == "snapshot_only":
            balance = snapshot_balance
            source_used = "snapshot" if snapshot_balance is not None else "none"
        else:
            if snapshot_balance is not None:
                balance = snapshot_balance
                source_used = "snapshot"
            else:
                balance = ledger_balance
                source_used = "ledger"

        result.append(
            {
                "account_id": entry["account_id"],
                "code": entry["code"],
                "name": entry["name"],
                "account_type": entry["account_type"],
                "balance": balance,
                "currency": "USD",
                "source_used": source_used,
                "ledger_balance": ledger_balance,
                "snapshot_balance": snapshot_balance,
                "snapshot_date": entry["snapshot_date"],
            }
        )

    return result
