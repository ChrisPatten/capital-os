from __future__ import annotations

from time import perf_counter

from capital_os.db.session import transaction
from capital_os.domain.posture.engine import PostureComputationInputs, compute_posture_metrics
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash
from capital_os.schemas.tools import ComputeCapitalPostureIn, ComputeCapitalPostureOut


def handle(payload: dict) -> ComputeCapitalPostureOut:
    started = perf_counter()
    req = ComputeCapitalPostureIn.model_validate(payload)
    input_hash = payload_hash(req.model_dump(mode="json"))

    metrics = compute_posture_metrics(
        PostureComputationInputs(
            liquidity=req.liquidity,
            fixed_burn=req.fixed_burn,
            variable_burn=req.variable_burn,
            minimum_reserve=req.minimum_reserve,
            volatility_buffer=req.volatility_buffer,
        )
    )
    response_payload = {
        "fixed_burn": f"{metrics.fixed_burn:.4f}",
        "variable_burn": f"{metrics.variable_burn:.4f}",
        "volatility_buffer": f"{metrics.volatility_buffer:.4f}",
        "reserve_target": f"{metrics.reserve_target:.4f}",
        "liquidity": f"{metrics.liquidity:.4f}",
        "liquidity_surplus": f"{metrics.liquidity_surplus:.4f}",
        "reserve_ratio": f"{metrics.reserve_ratio:.4f}",
        "risk_band": metrics.risk_band,
        "explanation": {
            "contributing_balances": [
                {"name": "liquidity", "amount": f"{metrics.liquidity:.4f}"},
                {"name": "fixed_burn", "amount": f"{metrics.fixed_burn:.4f}"},
                {"name": "variable_burn", "amount": f"{metrics.variable_burn:.4f}"},
            ],
            "reserve_assumptions": {
                "minimum_reserve": f"{req.minimum_reserve:.4f}",
                "volatility_buffer": f"{metrics.volatility_buffer:.4f}",
                "reserve_target": f"{metrics.reserve_target:.4f}",
            },
        },
        "correlation_id": req.correlation_id,
    }
    response_payload["output_hash"] = payload_hash(response_payload)

    with transaction() as conn:
        log_event(
            conn,
            tool_name="compute_capital_posture",
            correlation_id=req.correlation_id,
            input_hash=input_hash,
            output_hash=response_payload["output_hash"],
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )

    return ComputeCapitalPostureOut.model_validate(response_payload)
