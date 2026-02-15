from __future__ import annotations

from time import perf_counter

from capital_os.db.session import transaction
from capital_os.domain.query.service import query_config
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash
from capital_os.schemas.tools import GetConfigIn, GetConfigOut


def handle(payload: dict) -> GetConfigOut:
    started = perf_counter()
    req = GetConfigIn.model_validate(payload)
    input_hash = payload_hash(req.model_dump(mode="json"))

    config = query_config()
    response_payload = {
        "runtime": config["runtime"],
        "policy_rules": config["policy_rules"],
        "correlation_id": req.correlation_id,
    }
    response_payload["output_hash"] = payload_hash(response_payload)

    with transaction() as conn:
        log_event(
            conn,
            tool_name="get_config",
            correlation_id=req.correlation_id,
            input_hash=input_hash,
            output_hash=response_payload["output_hash"],
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )

    return GetConfigOut.model_validate(response_payload)
