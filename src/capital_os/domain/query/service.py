from __future__ import annotations

from capital_os.config import get_settings
from capital_os.db.session import read_only_connection
from capital_os.domain.ledger.repository import (
    fetch_proposal_with_decisions,
    fetch_transaction_with_postings_by_external_id,
    fetch_account_balances_as_of,
    fetch_account_tree_rows,
    list_obligations_page,
    list_policy_rules,
    list_proposals_page,
    list_transactions_page,
    list_accounts_page,
)
from capital_os.domain.query.pagination import decode_cursor, decode_cursor_payload, encode_cursor


def query_accounts_page(*, limit: int, cursor: str | None) -> dict:
    cursor_keys: dict[str, str] | None = None
    if cursor:
        cursor_payload = decode_cursor(cursor)
        cursor_keys = {"code": cursor_payload["code"], "account_id": cursor_payload["account_id"]}

    with read_only_connection() as conn:
        rows = list_accounts_page(conn, limit=limit, cursor=cursor_keys)

    next_cursor: str | None = None
    if len(rows) > limit:
        tail = rows[limit - 1]
        rows = rows[:limit]
        next_cursor = encode_cursor({"v": 1, "code": tail["code"], "account_id": tail["account_id"]})

    return {"accounts": rows, "next_cursor": next_cursor}


def query_account_tree(root_account_id: str | None) -> dict:
    with read_only_connection() as conn:
        rows = fetch_account_tree_rows(conn, root_account_id)

    nodes: dict[str, dict] = {}
    for row in rows:
        nodes[row["account_id"]] = {
            "account_id": row["account_id"],
            "code": row["code"],
            "name": row["name"],
            "account_type": row["account_type"],
            "parent_account_id": row["parent_account_id"],
            "metadata": row["metadata"],
            "children": [],
        }

    roots: list[dict] = []
    for row in rows:
        node = nodes[row["account_id"]]
        parent_id = row["parent_account_id"]
        if parent_id and parent_id in nodes:
            nodes[parent_id]["children"].append(node)
        else:
            roots.append(node)

    return {"root_account_id": root_account_id, "accounts": roots}


def query_account_balances(*, as_of_date: str, source_policy: str | None) -> dict:
    resolved_policy = source_policy or get_settings().balance_source_policy
    with read_only_connection() as conn:
        rows = fetch_account_balances_as_of(conn, as_of_date=as_of_date, source_policy=resolved_policy)
    return {"as_of_date": as_of_date, "source_policy": resolved_policy, "balances": rows}


def query_transactions_page(*, limit: int, cursor: str | None) -> dict:
    cursor_keys: dict[str, str] | None = None
    if cursor:
        cursor_payload = decode_cursor_payload(
            cursor, required_keys=("transaction_date", "transaction_id")
        )
        cursor_keys = {
            "transaction_date": cursor_payload["transaction_date"],
            "transaction_id": cursor_payload["transaction_id"],
        }

    with read_only_connection() as conn:
        rows = list_transactions_page(conn, limit=limit, cursor=cursor_keys)

    next_cursor: str | None = None
    if len(rows) > limit:
        tail = rows[limit - 1]
        rows = rows[:limit]
        next_cursor = encode_cursor(
            {"v": 1, "transaction_date": tail["transaction_date"], "transaction_id": tail["transaction_id"]}
        )
    return {"transactions": rows, "next_cursor": next_cursor}


def query_transaction_by_external_id(*, source_system: str, external_id: str) -> dict:
    with read_only_connection() as conn:
        transaction = fetch_transaction_with_postings_by_external_id(
            conn, source_system=source_system, external_id=external_id
        )
    return {"transaction": transaction}


def query_obligations_page(*, limit: int, cursor: str | None, active_only: bool) -> dict:
    cursor_keys: dict[str, str] | None = None
    if cursor:
        cursor_payload = decode_cursor_payload(cursor, required_keys=("next_due_date", "obligation_id"))
        cursor_keys = {
            "next_due_date": cursor_payload["next_due_date"],
            "obligation_id": cursor_payload["obligation_id"],
        }

    with read_only_connection() as conn:
        rows = list_obligations_page(conn, limit=limit, cursor=cursor_keys, active_only=active_only)

    next_cursor: str | None = None
    if len(rows) > limit:
        tail = rows[limit - 1]
        rows = rows[:limit]
        next_cursor = encode_cursor(
            {"v": 1, "next_due_date": tail["next_due_date"], "obligation_id": tail["obligation_id"]}
        )
    return {"obligations": rows, "next_cursor": next_cursor}


def query_proposals_page(*, limit: int, cursor: str | None, status: str | None) -> dict:
    cursor_keys: dict[str, str] | None = None
    if cursor:
        cursor_payload = decode_cursor_payload(cursor, required_keys=("created_at", "proposal_id"))
        cursor_keys = {"created_at": cursor_payload["created_at"], "proposal_id": cursor_payload["proposal_id"]}

    with read_only_connection() as conn:
        rows = list_proposals_page(conn, limit=limit, cursor=cursor_keys, status=status)

    next_cursor: str | None = None
    if len(rows) > limit:
        tail = rows[limit - 1]
        rows = rows[:limit]
        next_cursor = encode_cursor({"v": 1, "created_at": tail["created_at"], "proposal_id": tail["proposal_id"]})
    return {"proposals": rows, "next_cursor": next_cursor}


def query_proposal(*, proposal_id: str) -> dict:
    with read_only_connection() as conn:
        proposal = fetch_proposal_with_decisions(conn, proposal_id=proposal_id)
    return {"proposal": proposal}


def query_config() -> dict:
    settings = get_settings()
    with read_only_connection() as conn:
        rules = list_policy_rules(conn)
    return {
        "runtime": {
            "balance_source_policy": settings.balance_source_policy,
            "approval_threshold_amount": settings.approval_threshold_amount,
        },
        "policy_rules": rules,
    }
