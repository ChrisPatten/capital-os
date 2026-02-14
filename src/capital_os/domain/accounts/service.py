from __future__ import annotations

from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account, list_accounts_subtree


def create_account_entry(payload: dict) -> dict:
    with transaction() as conn:
        account_id = create_account(conn, payload)
    return {"account_id": account_id}


def list_account_subtree(root_account_id: str | None = None) -> dict:
    with transaction() as conn:
        rows = list_accounts_subtree(conn, root_account_id)
    return {"accounts": rows}
