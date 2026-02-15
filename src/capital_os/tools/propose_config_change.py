from __future__ import annotations

from time import perf_counter
from decimal import Decimal

from capital_os.db.session import transaction
from capital_os.domain.approval.repository import (
    fetch_proposal_by_source_external,
    insert_proposal,
    persist_proposal_result,
)
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash
from capital_os.schemas.tools import ProposeConfigChangeIn, ProposeConfigChangeOut


def _build_response(req: ProposeConfigChangeIn, proposal_id: str, status: str) -> dict:
    response = {
        "status": status,
        "proposal_id": proposal_id,
        "required_approvals": 1,
        "approvals_received": 0,
        "correlation_id": req.correlation_id,
    }
    response["output_hash"] = payload_hash(response)
    return response


def handle(payload: dict) -> ProposeConfigChangeOut:
    started = perf_counter()
    req = ProposeConfigChangeIn.model_validate(payload)
    input_hash = payload_hash(req.model_dump(mode="json"))

    with transaction() as conn:
        proposal = fetch_proposal_by_source_external(
            conn,
            tool_name="propose_config_change",
            source_system=req.source_system,
            external_id=req.external_id,
        )

        status = "proposed"
        if proposal is None:
            proposal_id = insert_proposal(
                conn,
                tool_name="propose_config_change",
                source_system=req.source_system,
                external_id=req.external_id,
                correlation_id=req.correlation_id,
                input_hash=input_hash,
                policy_threshold_amount=str(Decimal("0.0000")),
                impact_amount=str(Decimal("0.0000")),
                request_payload={"scope": req.scope, "change_payload": req.change_payload},
                matched_rule_id=None,
                required_approvals=1,
            )
        else:
            proposal_id = proposal["proposal_id"]
            status = "idempotent-replay"

        response_payload = _build_response(req, proposal_id, status)

        if proposal is None or not proposal.get("response_payload"):
            persist_proposal_result(
                conn,
                proposal_id=proposal_id,
                status="proposed",
                response_payload=response_payload,
                output_hash=response_payload["output_hash"],
            )

        log_event(
            conn,
            tool_name="propose_config_change",
            correlation_id=req.correlation_id,
            input_hash=input_hash,
            output_hash=response_payload["output_hash"],
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )

    return ProposeConfigChangeOut.model_validate(response_payload)
