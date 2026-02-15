from __future__ import annotations

from time import perf_counter

from capital_os.db.session import transaction
from capital_os.domain.query.service import query_accounts_page
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash
from capital_os.schemas.tools import ListAccountsIn, ListAccountsOut


def handle(payload: dict) -> ListAccountsOut:
    started = perf_counter()
    req = ListAccountsIn.model_validate(payload)
    input_hash = payload_hash(req.model_dump(mode="json"))

    page = query_accounts_page(limit=req.limit, cursor=req.cursor)
    response_payload = {
        "accounts": page["accounts"],
        "next_cursor": page["next_cursor"],
        "correlation_id": req.correlation_id,
    }
    response_payload["output_hash"] = payload_hash(response_payload)

    with transaction() as conn:
        log_event(
            conn,
            tool_name="list_accounts",
            correlation_id=req.correlation_id,
            input_hash=input_hash,
            output_hash=response_payload["output_hash"],
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )

    return ListAccountsOut.model_validate(response_payload)

