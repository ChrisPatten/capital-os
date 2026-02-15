from __future__ import annotations

from capital_os.db.session import read_only_connection
from capital_os.domain.ledger.repository import (
    fetch_account_balances_as_of,
    fetch_account_tree_rows,
    list_accounts_page,
)
from capital_os.domain.query.pagination import decode_cursor, encode_cursor


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


def query_account_balances(*, as_of_date: str, source_policy: str) -> dict:
    with read_only_connection() as conn:
        rows = fetch_account_balances_as_of(conn, as_of_date=as_of_date, source_policy=source_policy)
    return {"as_of_date": as_of_date, "source_policy": source_policy, "balances": rows}

