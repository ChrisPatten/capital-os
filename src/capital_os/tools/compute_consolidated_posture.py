from __future__ import annotations

from time import perf_counter

from capital_os.db.session import transaction
from capital_os.domain.posture.consolidation import compute_consolidated_posture as consolidate
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash
from capital_os.schemas.tools import ComputeConsolidatedPostureIn, ComputeConsolidatedPostureOut


def handle(payload: dict) -> ComputeConsolidatedPostureOut:
    started = perf_counter()
    req = ComputeConsolidatedPostureIn.model_validate(payload)
    input_hash = payload_hash(req.model_dump(mode="json"))

    consolidated = consolidate(req.model_dump(mode="json", exclude={"correlation_id"}))
    response_payload = {
        "entity_ids": consolidated["entity_ids"],
        "entities": consolidated["entities"],
        "transfer_pairs": consolidated["transfer_pairs"],
        "fixed_burn": consolidated["fixed_burn"],
        "variable_burn": consolidated["variable_burn"],
        "volatility_buffer": consolidated["volatility_buffer"],
        "reserve_target": consolidated["reserve_target"],
        "liquidity": consolidated["liquidity"],
        "liquidity_surplus": consolidated["liquidity_surplus"],
        "reserve_ratio": consolidated["reserve_ratio"],
        "risk_band": consolidated["risk_band"],
        "correlation_id": req.correlation_id,
    }
    response_payload["output_hash"] = payload_hash(response_payload)

    with transaction() as conn:
        log_event(
            conn,
            tool_name="compute_consolidated_posture",
            correlation_id=req.correlation_id,
            input_hash=input_hash,
            output_hash=response_payload["output_hash"],
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )

    return ComputeConsolidatedPostureOut.model_validate(response_payload)
