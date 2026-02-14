from __future__ import annotations

from time import perf_counter

from capital_os.db.session import transaction
from capital_os.domain.simulation.service import simulate_spend as simulate_spend_projection
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash
from capital_os.schemas.tools import SimulateSpendIn, SimulateSpendOut


def handle(payload: dict) -> SimulateSpendOut:
    started = perf_counter()
    req = SimulateSpendIn.model_validate(payload)
    input_hash = payload_hash(req.model_dump(mode="json"))

    projection = simulate_spend_projection(req.model_dump(mode="json", exclude={"correlation_id"}))
    response_payload = {
        "starting_liquidity": projection["starting_liquidity"],
        "periods": projection["periods"],
        "correlation_id": req.correlation_id,
    }
    response_payload["output_hash"] = payload_hash(response_payload)

    with transaction() as conn:
        log_event(
            conn,
            tool_name="simulate_spend",
            correlation_id=req.correlation_id,
            input_hash=input_hash,
            output_hash=response_payload["output_hash"],
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )

    return SimulateSpendOut.model_validate(response_payload)
