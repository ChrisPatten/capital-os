from __future__ import annotations

from time import perf_counter

from capital_os.db.session import transaction
from capital_os.domain.query.service import query_obligations_page
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash
from capital_os.schemas.tools import ListObligationsIn, ListObligationsOut


_NEW_KEYS = ("recurrence", "day_of_month", "funding_account_id", "bucket")


def handle(payload: dict) -> ListObligationsOut:
    started = perf_counter()
    req = ListObligationsIn.model_validate(payload)
    input_hash = payload_hash(req.model_dump(mode="json"))

    page = query_obligations_page(limit=req.limit, cursor=req.cursor, active_only=req.active_only)
    # Omit null recurrence fields from the hashed payload so rows that predate migration 0013
    # keep the exact output_hash they had before the columns existed.
    obligations = [
        {k: v for k, v in row.items() if not (k in _NEW_KEYS and v is None)}
        for row in page["obligations"]
    ]
    response_payload = {
        "obligations": obligations,
        "next_cursor": page["next_cursor"],
        "correlation_id": req.correlation_id,
    }
    response_payload["output_hash"] = payload_hash(response_payload)

    with transaction() as conn:
        log_event(
            conn,
            tool_name="list_obligations",
            correlation_id=req.correlation_id,
            input_hash=input_hash,
            output_hash=response_payload["output_hash"],
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )

    return ListObligationsOut.model_validate(response_payload)
