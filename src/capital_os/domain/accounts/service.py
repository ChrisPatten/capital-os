from __future__ import annotations

import sqlite3
from time import perf_counter

from capital_os.db.session import transaction
from capital_os.domain.entities import DEFAULT_ENTITY_ID
from capital_os.domain.ledger.repository import create_account, list_accounts_subtree
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash


def create_account_entry(payload: dict) -> dict:
    started = perf_counter()
    input_hash = payload_hash(payload)
    try:
        with transaction() as conn:
            entity_id = payload.get("entity_id", DEFAULT_ENTITY_ID)
            parent_account_id = payload.get("parent_account_id")

            if parent_account_id is not None:
                row = conn.execute(
                    "SELECT account_id FROM accounts WHERE account_id = ?",
                    (parent_account_id,),
                ).fetchone()
                if row is None:
                    raise ValueError(f"parent_account_id '{parent_account_id}' does not exist")

            if entity_id != DEFAULT_ENTITY_ID:
                row = conn.execute(
                    "SELECT entity_id FROM entities WHERE entity_id = ?",
                    (entity_id,),
                ).fetchone()
                if row is None:
                    raise ValueError(f"entity_id '{entity_id}' does not exist")

            account_id = create_account(conn, payload)

            response = {
                "account_id": account_id,
                "status": "committed",
                "correlation_id": payload["correlation_id"],
            }
            output_hash = payload_hash(response)
            response["output_hash"] = output_hash

            log_event(
                conn,
                tool_name="create_account",
                correlation_id=payload["correlation_id"],
                input_hash=input_hash,
                output_hash=output_hash,
                duration_ms=int((perf_counter() - started) * 1000),
                status="ok",
            )
            return response
    except sqlite3.IntegrityError as exc:
        msg = str(exc).lower()
        if "unique" in msg and "code" in msg:
            raise ValueError(f"account code '{payload.get('code')}' already exists") from exc
        if "cycle" in msg or "hierarchy" in msg:
            raise ValueError("account hierarchy cycle detected") from exc
        raise ValueError(str(exc)) from exc


def list_account_subtree(root_account_id: str | None = None) -> dict:
    with transaction() as conn:
        rows = list_accounts_subtree(conn, root_account_id)
    return {"accounts": rows}
