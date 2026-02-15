from __future__ import annotations

from time import perf_counter

from capital_os.db.session import transaction
from capital_os.domain.debt.service import analyze_debt as analyze_debt_projection
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash
from capital_os.schemas.tools import AnalyzeDebtIn, AnalyzeDebtOut


def handle(payload: dict) -> AnalyzeDebtOut:
    started = perf_counter()
    req = AnalyzeDebtIn.model_validate(payload)
    input_hash = payload_hash(req.model_dump(mode="json"))

    projection = analyze_debt_projection(req.model_dump(mode="json", exclude={"correlation_id"}))
    response_payload = {
        "optional_payoff_amount": projection["optional_payoff_amount"],
        "reserve_floor": projection["reserve_floor"],
        "total_interest_saved": projection["total_interest_saved"],
        "total_cashflow_freed": projection["total_cashflow_freed"],
        "total_reserve_impact": projection["total_reserve_impact"],
        "ranked_liabilities": projection["ranked_liabilities"],
        "correlation_id": req.correlation_id,
    }
    response_payload["output_hash"] = payload_hash(response_payload)

    with transaction() as conn:
        log_event(
            conn,
            tool_name="analyze_debt",
            correlation_id=req.correlation_id,
            input_hash=input_hash,
            output_hash=response_payload["output_hash"],
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )

    return AnalyzeDebtOut.model_validate(response_payload)
