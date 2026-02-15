from __future__ import annotations

from time import perf_counter

from capital_os.db.session import transaction
from capital_os.domain.reconciliation.service import reconcile_account
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash
from capital_os.schemas.tools import ReconcileAccountIn, ReconcileAccountOut


def handle(payload: dict) -> ReconcileAccountOut:
    started = perf_counter()
    req = ReconcileAccountIn.model_validate(payload)
    input_hash = payload_hash(req.model_dump(mode="json"))

    reconciliation = reconcile_account(req.model_dump(mode="json"))
    response_payload = {
        **reconciliation,
        "correlation_id": req.correlation_id,
    }
    response_payload["output_hash"] = payload_hash(response_payload)

    with transaction() as conn:
        log_event(
            conn,
            tool_name="reconcile_account",
            correlation_id=req.correlation_id,
            input_hash=input_hash,
            output_hash=response_payload["output_hash"],
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )

    return ReconcileAccountOut.model_validate(response_payload)
