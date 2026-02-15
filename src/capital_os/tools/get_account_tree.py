from __future__ import annotations

from time import perf_counter

from capital_os.db.session import transaction
from capital_os.domain.query.service import query_account_tree
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash
from capital_os.schemas.tools import GetAccountTreeIn, GetAccountTreeOut


def handle(payload: dict) -> GetAccountTreeOut:
    started = perf_counter()
    req = GetAccountTreeIn.model_validate(payload)
    input_hash = payload_hash(req.model_dump(mode="json"))

    tree = query_account_tree(req.root_account_id)
    response_payload = {
        "root_account_id": tree["root_account_id"],
        "accounts": tree["accounts"],
        "correlation_id": req.correlation_id,
    }
    response_payload["output_hash"] = payload_hash(response_payload)

    with transaction() as conn:
        log_event(
            conn,
            tool_name="get_account_tree",
            correlation_id=req.correlation_id,
            input_hash=input_hash,
            output_hash=response_payload["output_hash"],
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )

    return GetAccountTreeOut.model_validate(response_payload)

