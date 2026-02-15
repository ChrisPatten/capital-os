from __future__ import annotations

from time import perf_counter

from capital_os.db.session import transaction
from capital_os.domain.query.service import query_account_balances
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash
from capital_os.schemas.tools import GetAccountBalancesIn, GetAccountBalancesOut


def handle(payload: dict) -> GetAccountBalancesOut:
    started = perf_counter()
    req = GetAccountBalancesIn.model_validate(payload)
    input_hash = payload_hash(req.model_dump(mode="json"))

    balances = query_account_balances(
        as_of_date=req.as_of_date.isoformat(), source_policy=req.source_policy
    )
    response_payload = {
        "as_of_date": balances["as_of_date"],
        "source_policy": balances["source_policy"],
        "balances": balances["balances"],
        "correlation_id": req.correlation_id,
    }
    response_payload["output_hash"] = payload_hash(response_payload)

    with transaction() as conn:
        log_event(
            conn,
            tool_name="get_account_balances",
            correlation_id=req.correlation_id,
            input_hash=input_hash,
            output_hash=response_payload["output_hash"],
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )

    return GetAccountBalancesOut.model_validate(response_payload)

