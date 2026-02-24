from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from capital_os.domain.entities import DEFAULT_ENTITY_ID
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
            transaction_id, source_system, external_id, transaction_date, description, correlation_id, input_hash, entity_id,
            is_adjusting_entry, adjusting_reason_code
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            tx_id,
            payload["source_system"],
            payload["external_id"],
            payload["date"],
            payload["description"],
            payload["correlation_id"],
            payload["input_hash"],
            payload.get("entity_id", DEFAULT_ENTITY_ID),
            1 if payload.get("is_adjusting_entry", False) else 0,
            payload.get("adjusting_reason_code"),
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
            SET balance=?, currency=?, source_artifact_id=?, source_system=?, entity_id=?, updated_at=CURRENT_TIMESTAMP
            WHERE snapshot_id=?
            """,
            (
                str(normalize_amount(payload["balance"])),
                payload["currency"],
                payload.get("source_artifact_id"),
                payload["source_system"],
                payload.get("entity_id", DEFAULT_ENTITY_ID),
                snapshot_id,
            ),
        )
        return snapshot_id, "updated"

    snapshot_id = str(uuid4())
    conn.execute(
        """
        INSERT INTO balance_snapshots (
            snapshot_id, source_system, account_id, snapshot_date, balance, currency, source_artifact_id, entity_id
        ) VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            snapshot_id,
            payload["source_system"],
            payload["account_id"],
            str(payload["snapshot_date"]),
            str(normalize_amount(payload["balance"])),
            payload["currency"],
            payload.get("source_artifact_id"),
            payload.get("entity_id", DEFAULT_ENTITY_ID),
        ),
    )
    return snapshot_id, "recorded"


def upsert_obligation(conn, payload: dict[str, Any]) -> tuple[str, str, bool]:
    active_flag = 1 if payload.get("active", True) else 0
    existing = conn.execute(
        "SELECT obligation_id FROM obligations WHERE source_system=? AND name=? AND account_id=?",
        (payload["source_system"], payload["name"], payload["account_id"]),
    ).fetchone()
    if existing:
        obligation_id = str(existing["obligation_id"])
        conn.execute(
            """
            UPDATE obligations
            SET cadence=?, expected_amount=?, variability_flag=?, next_due_date=?, metadata=?, entity_id=?, active=?, updated_at=CURRENT_TIMESTAMP
            WHERE obligation_id=?
            """,
            (
                payload["cadence"],
                str(normalize_amount(payload["expected_amount"])),
                1 if payload.get("variability_flag", False) else 0,
                str(payload["next_due_date"]),
                json.dumps(payload.get("metadata", {}), separators=(",", ":")),
                payload.get("entity_id", DEFAULT_ENTITY_ID),
                active_flag,
                obligation_id,
            ),
        )
        return obligation_id, "updated", bool(active_flag)

    obligation_id = str(uuid4())
    conn.execute(
        """
        INSERT INTO obligations (
            obligation_id, source_system, name, account_id, cadence, expected_amount,
            variability_flag, next_due_date, metadata, active, entity_id
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
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
            active_flag,
            payload.get("entity_id", DEFAULT_ENTITY_ID),
        ),
    )
    return obligation_id, "created", bool(active_flag)


def fulfill_obligation(conn, payload: dict[str, Any]) -> dict[str, Any]:
    """Set active=0 on an obligation, recording fulfillment linkage."""
    existing = conn.execute(
        "SELECT obligation_id, active, fulfilled_by_transaction_id, fulfilled_at FROM obligations WHERE obligation_id=?",
        (payload["obligation_id"],),
    ).fetchone()
    if not existing:
        raise ValueError(f"obligation not found: {payload['obligation_id']}")

    if not existing["active"]:
        return {
            "status": "already_fulfilled",
            "obligation_id": str(existing["obligation_id"]),
            "fulfilled_by_transaction_id": existing["fulfilled_by_transaction_id"],
            "fulfilled_at": existing["fulfilled_at"],
        }

    from datetime import datetime, timezone
    fulfilled_at = payload.get("fulfilled_at")
    if fulfilled_at is None:
        fulfilled_at = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    elif not isinstance(fulfilled_at, str):
        fulfilled_at = fulfilled_at.isoformat(timespec="microseconds")

    fulfilled_by_transaction_id = payload.get("fulfilled_by_transaction_id")

    conn.execute(
        """
        UPDATE obligations
        SET active=0, fulfilled_by_transaction_id=?, fulfilled_at=?, updated_at=CURRENT_TIMESTAMP
        WHERE obligation_id=?
        """,
        (fulfilled_by_transaction_id, fulfilled_at, str(existing["obligation_id"])),
    )
    return {
        "status": "fulfilled",
        "obligation_id": str(existing["obligation_id"]),
        "fulfilled_by_transaction_id": fulfilled_by_transaction_id,
        "fulfilled_at": fulfilled_at,
    }


def create_account(conn, payload: dict[str, Any]) -> str:
    account_id = str(uuid4())
    conn.execute(
        """
        INSERT INTO accounts (account_id, code, name, account_type, parent_account_id, metadata, entity_id)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            account_id,
            payload["code"],
            payload["name"],
            payload["account_type"],
            payload.get("parent_account_id"),
            json.dumps(payload.get("metadata", {}), separators=(",", ":")),
            payload.get("entity_id", DEFAULT_ENTITY_ID),
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


def fetch_account_balance_context(conn, *, account_id: str, as_of_date: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        WITH ledger_total AS (
            SELECT COALESCE(SUM(p.amount), 0) AS ledger_balance
            FROM ledger_postings p
            JOIN ledger_transactions t ON t.transaction_id = p.transaction_id
            WHERE p.account_id = ? AND date(t.transaction_date) <= date(?)
        ),
        latest_snapshot AS (
            SELECT s.balance AS snapshot_balance, s.snapshot_date
            FROM balance_snapshots s
            WHERE s.account_id = ? AND date(s.snapshot_date) <= date(?)
            ORDER BY s.snapshot_date DESC, s.snapshot_id DESC
            LIMIT 1
        )
        SELECT
          a.account_id,
          a.code,
          a.name,
          a.account_type,
          (SELECT ledger_balance FROM ledger_total) AS ledger_balance,
          ls.snapshot_balance,
          ls.snapshot_date
        FROM accounts a
        LEFT JOIN latest_snapshot ls ON 1=1
        WHERE a.account_id = ?
        """,
        (account_id, as_of_date, account_id, as_of_date, account_id),
    ).fetchone()
    if not row:
        return None
    return dict(row)


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


def list_transactions_page(conn, *, limit: int, cursor: dict[str, str] | None) -> list[dict[str, Any]]:
    where_clause = ""
    params: tuple[Any, ...]
    if cursor:
        where_clause = "WHERE (t.transaction_date < ? OR (t.transaction_date = ? AND t.transaction_id > ?))"
        params = (cursor["transaction_date"], cursor["transaction_date"], cursor["transaction_id"], limit + 1)
    else:
        params = (limit + 1,)

    rows = conn.execute(
        f"""
        SELECT
          t.transaction_id,
          t.source_system,
          t.external_id,
          t.transaction_date,
          t.description,
          t.correlation_id,
          t.entity_id,
          t.created_at,
          COUNT(p.posting_id) AS posting_count,
          COALESCE(SUM(ABS(p.amount)), 0) AS gross_posting_amount
        FROM ledger_transactions t
        LEFT JOIN ledger_postings p ON p.transaction_id = t.transaction_id
        {where_clause}
        GROUP BY
          t.transaction_id,
          t.source_system,
          t.external_id,
          t.transaction_date,
          t.description,
          t.correlation_id,
          t.entity_id,
          t.created_at
        ORDER BY t.transaction_date DESC, t.transaction_id ASC
        LIMIT ?
        """,
        params,
    ).fetchall()

    return [
        {
            "transaction_id": row["transaction_id"],
            "source_system": row["source_system"],
            "external_id": row["external_id"],
            "transaction_date": row["transaction_date"],
            "description": row["description"],
            "correlation_id": row["correlation_id"],
            "entity_id": row["entity_id"],
            "created_at": row["created_at"],
            "posting_count": int(row["posting_count"]),
            "gross_posting_amount": normalize_amount(row["gross_posting_amount"]),
            "currency": "USD",
        }
        for row in rows
    ]


def fetch_transaction_with_postings_by_external_id(
    conn, *, source_system: str, external_id: str
) -> dict[str, Any] | None:
    tx_row = conn.execute(
        """
        SELECT
          transaction_id,
          source_system,
          external_id,
          transaction_date,
          description,
          correlation_id,
          entity_id,
          created_at
        FROM ledger_transactions
        WHERE source_system=? AND external_id=?
        """,
        (source_system, external_id),
    ).fetchone()
    if not tx_row:
        return None

    posting_rows = conn.execute(
        """
        SELECT
          p.posting_id,
          p.account_id,
          a.code AS account_code,
          a.name AS account_name,
          p.amount,
          p.currency,
          p.memo
        FROM ledger_postings p
        JOIN accounts a ON a.account_id = p.account_id
        WHERE p.transaction_id=?
        ORDER BY a.code ASC, p.posting_id ASC
        """,
        (tx_row["transaction_id"],),
    ).fetchall()
    postings = [
        {
            "posting_id": row["posting_id"],
            "account_id": row["account_id"],
            "account_code": row["account_code"],
            "account_name": row["account_name"],
            "amount": normalize_amount(row["amount"]),
            "currency": row["currency"],
            "memo": row["memo"],
        }
        for row in posting_rows
    ]

    return {
        "transaction_id": tx_row["transaction_id"],
        "source_system": tx_row["source_system"],
        "external_id": tx_row["external_id"],
        "transaction_date": tx_row["transaction_date"],
        "description": tx_row["description"],
        "correlation_id": tx_row["correlation_id"],
        "entity_id": tx_row["entity_id"],
        "created_at": tx_row["created_at"],
        "postings": postings,
    }


def list_obligations_page(
    conn, *, limit: int, cursor: dict[str, str] | None, active_only: bool
) -> list[dict[str, Any]]:
    where_parts: list[str] = []
    params: tuple[Any, ...]
    params_list: list[Any] = []
    if cursor:
        where_parts.append("(next_due_date > ? OR (next_due_date = ? AND obligation_id > ?))")
        params_list.extend([cursor["next_due_date"], cursor["next_due_date"], cursor["obligation_id"]])
    if active_only:
        where_parts.append("active = 1")

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    params_list.append(limit + 1)
    params = tuple(params_list)

    rows = conn.execute(
        f"""
        SELECT
          obligation_id,
          source_system,
          name,
          account_id,
          cadence,
          expected_amount,
          variability_flag,
          next_due_date,
          metadata,
          active,
          entity_id,
          created_at,
          updated_at
        FROM obligations
        {where_clause}
        ORDER BY next_due_date ASC, obligation_id ASC
        LIMIT ?
        """,
        params,
    ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        result.append(
            {
                "obligation_id": row["obligation_id"],
                "source_system": row["source_system"],
                "name": row["name"],
                "account_id": row["account_id"],
                "cadence": row["cadence"],
                "expected_amount": normalize_amount(row["expected_amount"]),
                "variability_flag": bool(row["variability_flag"]),
                "next_due_date": row["next_due_date"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "active": bool(row["active"]),
                "entity_id": row["entity_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
    return result


def list_proposals_page(
    conn, *, limit: int, cursor: dict[str, str] | None, status: str | None
) -> list[dict[str, Any]]:
    where_parts: list[str] = []
    params: tuple[Any, ...]
    params_list: list[Any] = []
    if cursor:
        where_parts.append("(created_at < ? OR (created_at = ? AND proposal_id > ?))")
        params_list.extend([cursor["created_at"], cursor["created_at"], cursor["proposal_id"]])
    if status:
        where_parts.append("status = ?")
        params_list.append(status)

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    params_list.append(limit + 1)
    params = tuple(params_list)

    rows = conn.execute(
        f"""
        SELECT
          proposal_id,
          tool_name,
          source_system,
          external_id,
          correlation_id,
          status,
          policy_threshold_amount,
          impact_amount,
          matched_rule_id,
          required_approvals,
          entity_id,
          created_at,
          updated_at
        FROM approval_proposals
        {where_clause}
        ORDER BY created_at DESC, proposal_id ASC
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [
        {
            "proposal_id": row["proposal_id"],
            "tool_name": row["tool_name"],
            "source_system": row["source_system"],
            "external_id": row["external_id"],
            "correlation_id": row["correlation_id"],
            "status": row["status"],
            "policy_threshold_amount": normalize_amount(row["policy_threshold_amount"]),
            "impact_amount": normalize_amount(row["impact_amount"]),
            "matched_rule_id": row["matched_rule_id"],
            "required_approvals": int(row["required_approvals"]),
            "entity_id": row["entity_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def fetch_proposal_with_decisions(conn, *, proposal_id: str) -> dict[str, Any] | None:
    proposal_row = conn.execute(
        """
        SELECT
          proposal_id,
          tool_name,
          source_system,
          external_id,
          correlation_id,
          input_hash,
          status,
          policy_threshold_amount,
          impact_amount,
          request_payload,
          response_payload,
          output_hash,
          decision_reason,
          approved_transaction_id,
          matched_rule_id,
          required_approvals,
          entity_id,
          created_at,
          updated_at
        FROM approval_proposals
        WHERE proposal_id=?
        """,
        (proposal_id,),
    ).fetchone()
    if not proposal_row:
        return None

    decisions = conn.execute(
        """
        SELECT decision_id, action, correlation_id, reason, approver_id, created_at
        FROM approval_decisions
        WHERE proposal_id=?
        ORDER BY created_at ASC, decision_id ASC
        """,
        (proposal_id,),
    ).fetchall()
    return {
        "proposal_id": proposal_row["proposal_id"],
        "tool_name": proposal_row["tool_name"],
        "source_system": proposal_row["source_system"],
        "external_id": proposal_row["external_id"],
        "correlation_id": proposal_row["correlation_id"],
        "input_hash": proposal_row["input_hash"],
        "status": proposal_row["status"],
        "policy_threshold_amount": normalize_amount(proposal_row["policy_threshold_amount"]),
        "impact_amount": normalize_amount(proposal_row["impact_amount"]),
        "request_payload": json.loads(proposal_row["request_payload"]) if proposal_row["request_payload"] else None,
        "response_payload": json.loads(proposal_row["response_payload"]) if proposal_row["response_payload"] else None,
        "output_hash": proposal_row["output_hash"],
        "decision_reason": proposal_row["decision_reason"],
        "approved_transaction_id": proposal_row["approved_transaction_id"],
        "matched_rule_id": proposal_row["matched_rule_id"],
        "required_approvals": int(proposal_row["required_approvals"]),
        "entity_id": proposal_row["entity_id"],
        "created_at": proposal_row["created_at"],
        "updated_at": proposal_row["updated_at"],
        "decisions": [
            {
                "decision_id": row["decision_id"],
                "action": row["action"],
                "correlation_id": row["correlation_id"],
                "reason": row["reason"],
                "approver_id": row["approver_id"],
                "created_at": row["created_at"],
            }
            for row in decisions
        ],
    }


def list_policy_rules(conn) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
          rule_id,
          priority,
          tool_name,
          entity_id,
          transaction_category,
          risk_band,
          velocity_limit_count,
          velocity_window_seconds,
          threshold_amount,
          required_approvals,
          active,
          metadata,
          created_at
        FROM policy_rules
        ORDER BY active DESC, priority ASC, rule_id ASC
        """
    ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        result.append(
            {
                "rule_id": row["rule_id"],
                "priority": int(row["priority"]),
                "tool_name": row["tool_name"],
                "entity_id": row["entity_id"],
                "transaction_category": row["transaction_category"],
                "risk_band": row["risk_band"],
                "velocity_limit_count": row["velocity_limit_count"],
                "velocity_window_seconds": row["velocity_window_seconds"],
                "threshold_amount": normalize_amount(row["threshold_amount"]),
                "required_approvals": int(row["required_approvals"]),
                "active": bool(row["active"]),
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "created_at": row["created_at"],
            }
        )
    return result
