from __future__ import annotations

from capital_os.domain.ledger.repository import fetch_transaction_by_external_id


def resolve_transaction_idempotency(conn, source_system: str, external_id: str) -> dict | None:
    row = fetch_transaction_by_external_id(conn, source_system, external_id)
    if not row:
        return None
    response = dict(row["response_payload"] or {})
    if response:
        response["status"] = "idempotent-replay"
    return response
