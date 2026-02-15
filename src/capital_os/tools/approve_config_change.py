from __future__ import annotations

from time import perf_counter

from capital_os.db.session import transaction
from capital_os.domain.approval.repository import (
    fetch_proposal_by_id,
    has_approver_decision,
    insert_decision,
    persist_proposal_result,
)
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash
from capital_os.schemas.tools import ApproveConfigChangeIn, ApproveConfigChangeOut


def handle(payload: dict) -> ApproveConfigChangeOut:
    started = perf_counter()
    req = ApproveConfigChangeIn.model_validate(payload)
    input_hash = payload_hash(req.model_dump(mode="json"))

    with transaction() as conn:
        proposal = fetch_proposal_by_id(conn, req.proposal_id)
        if proposal is None or proposal["tool_name"] != "propose_config_change":
            raise ValueError("config proposal not found")

        if proposal["status"] == "rejected":
            response_payload = {
                "status": "rejected",
                "proposal_id": proposal["proposal_id"],
                "approvals_received": 0,
                "required_approvals": 1,
                "applied_change": None,
                "correlation_id": req.correlation_id,
            }
        elif proposal["status"] == "committed":
            payload_body = proposal.get("request_payload") or {}
            response_payload = {
                "status": "already_applied",
                "proposal_id": proposal["proposal_id"],
                "approvals_received": 1,
                "required_approvals": 1,
                "applied_change": payload_body,
                "correlation_id": req.correlation_id,
            }
        else:
            if req.approver_id and has_approver_decision(
                conn,
                proposal_id=proposal["proposal_id"],
                action="approve",
                approver_id=req.approver_id,
            ):
                payload_body = proposal.get("request_payload") or {}
                response_payload = {
                    "status": "applied",
                    "proposal_id": proposal["proposal_id"],
                    "approvals_received": 1,
                    "required_approvals": 1,
                    "applied_change": payload_body,
                    "correlation_id": req.correlation_id,
                }
                response_payload["output_hash"] = payload_hash(response_payload)
                persist_proposal_result(
                    conn,
                    proposal_id=proposal["proposal_id"],
                    status="committed",
                    response_payload=response_payload,
                    output_hash=response_payload["output_hash"],
                    decision_reason=req.reason,
                )
            else:
                insert_decision(
                    conn,
                    proposal_id=proposal["proposal_id"],
                    action="approve",
                    correlation_id=req.correlation_id,
                    reason=req.reason,
                    approver_id=req.approver_id,
                )
                payload_body = proposal.get("request_payload") or {}
                response_payload = {
                    "status": "applied",
                    "proposal_id": proposal["proposal_id"],
                    "approvals_received": 1,
                    "required_approvals": 1,
                    "applied_change": payload_body,
                    "correlation_id": req.correlation_id,
                }
                response_payload["output_hash"] = payload_hash(response_payload)
                persist_proposal_result(
                    conn,
                    proposal_id=proposal["proposal_id"],
                    status="committed",
                    response_payload=response_payload,
                    output_hash=response_payload["output_hash"],
                    decision_reason=req.reason,
                )

        if "output_hash" not in response_payload:
            response_payload["output_hash"] = payload_hash(response_payload)

        log_event(
            conn,
            tool_name="approve_config_change",
            correlation_id=req.correlation_id,
            input_hash=input_hash,
            output_hash=response_payload["output_hash"],
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )

    return ApproveConfigChangeOut.model_validate(response_payload)
