from __future__ import annotations

from time import perf_counter

from capital_os.db.session import transaction
from capital_os.domain.query.service import query_transaction_by_external_id
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash
from capital_os.schemas.tools import GetTransactionByExternalIdIn, GetTransactionByExternalIdOut


def handle(payload: dict) -> GetTransactionByExternalIdOut:
    started = perf_counter()
    req = GetTransactionByExternalIdIn.model_validate(payload)
    input_hash = payload_hash(req.model_dump(mode="json"))

    result = query_transaction_by_external_id(source_system=req.source_system, external_id=req.external_id)
    response_payload = {
        "transaction": result["transaction"],
        "correlation_id": req.correlation_id,
    }
    response_payload["output_hash"] = payload_hash(response_payload)

    with transaction() as conn:
        log_event(
            conn,
            tool_name="get_transaction_by_external_id",
            correlation_id=req.correlation_id,
            input_hash=input_hash,
            output_hash=response_payload["output_hash"],
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )

    return GetTransactionByExternalIdOut.model_validate(response_payload)
