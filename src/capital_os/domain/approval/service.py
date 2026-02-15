from __future__ import annotations

from time import perf_counter
import sqlite3

from capital_os.db.session import transaction
from capital_os.domain.approval.repository import (
    fetch_proposal_by_id,
    insert_decision,
    persist_proposal_result,
)
from capital_os.domain.ledger.idempotency import resolve_transaction_idempotency
from capital_os.domain.ledger.invariants import InvariantError
from capital_os.domain.ledger.repository import insert_transaction_bundle, save_transaction_response
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash



def _proposal_committed_response(proposal: dict) -> dict:
    response = dict(proposal.get("response_payload") or {})
    if not response:
        raise InvariantError("proposal is committed but missing response payload")
    return response



def approve_proposed_transaction(payload: dict) -> dict:
    started = perf_counter()
    input_hash = payload_hash(payload)

    with transaction() as conn:
        proposal = fetch_proposal_by_id(conn, payload["proposal_id"])
        if not proposal:
            raise InvariantError("proposal not found")

        if proposal["status"] == "rejected":
            raise InvariantError("rejected proposals cannot be approved")

        if proposal["status"] == "committed":
            response = _proposal_committed_response(proposal)
            output_hash = response.get("output_hash") or payload_hash(response)
            response["output_hash"] = output_hash
            insert_decision(
                conn,
                proposal_id=proposal["proposal_id"],
                action="approve",
                correlation_id=payload["correlation_id"],
                reason=payload.get("reason"),
            )
            log_event(
                conn,
                tool_name="approve_proposed_transaction",
                correlation_id=payload["correlation_id"],
                input_hash=input_hash,
                output_hash=output_hash,
                duration_ms=int((perf_counter() - started) * 1000),
                status="ok",
            )
            return response

        request_payload = dict(proposal["request_payload"])
        request_payload["input_hash"] = proposal["input_hash"]

        response: dict
        try:
            transaction_id, posting_ids = insert_transaction_bundle(conn, request_payload)
            response = {
                "status": "committed",
                "proposal_id": proposal["proposal_id"],
                "transaction_id": transaction_id,
                "posting_ids": posting_ids,
                "correlation_id": proposal["correlation_id"],
            }
            output_hash = payload_hash(response)
            response["output_hash"] = output_hash
            save_transaction_response(conn, transaction_id, response, output_hash)
        except sqlite3.IntegrityError:
            replay = resolve_transaction_idempotency(
                conn,
                request_payload["source_system"],
                request_payload["external_id"],
            )
            if not replay:
                raise
            output_hash = replay.get("output_hash") or payload_hash(replay)
            response = {
                "status": "committed",
                "proposal_id": proposal["proposal_id"],
                "transaction_id": replay["transaction_id"],
                "posting_ids": replay["posting_ids"],
                "correlation_id": proposal["correlation_id"],
                "output_hash": output_hash,
            }

        persist_proposal_result(
            conn,
            proposal_id=proposal["proposal_id"],
            status="committed",
            response_payload=response,
            output_hash=response["output_hash"],
            decision_reason=payload.get("reason"),
            approved_transaction_id=response["transaction_id"],
        )
        insert_decision(
            conn,
            proposal_id=proposal["proposal_id"],
            action="approve",
            correlation_id=payload["correlation_id"],
            reason=payload.get("reason"),
        )
        log_event(
            conn,
            tool_name="approve_proposed_transaction",
            correlation_id=payload["correlation_id"],
            input_hash=input_hash,
            output_hash=response["output_hash"],
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )
        return response



def reject_proposed_transaction(payload: dict) -> dict:
    started = perf_counter()
    input_hash = payload_hash(payload)

    with transaction() as conn:
        proposal = fetch_proposal_by_id(conn, payload["proposal_id"])
        if not proposal:
            raise InvariantError("proposal not found")

        if proposal["status"] == "committed":
            raise InvariantError("committed proposals cannot be rejected")

        if proposal["status"] == "rejected" and proposal.get("response_payload"):
            response = dict(proposal["response_payload"])
            output_hash = response.get("output_hash") or payload_hash(response)
            response["output_hash"] = output_hash
            insert_decision(
                conn,
                proposal_id=proposal["proposal_id"],
                action="reject",
                correlation_id=payload["correlation_id"],
                reason=payload.get("reason"),
            )
            log_event(
                conn,
                tool_name="reject_proposed_transaction",
                correlation_id=payload["correlation_id"],
                input_hash=input_hash,
                output_hash=output_hash,
                duration_ms=int((perf_counter() - started) * 1000),
                status="ok",
            )
            return response

        response = {
            "status": "rejected",
            "proposal_id": proposal["proposal_id"],
            "reason": payload.get("reason"),
            "correlation_id": proposal["correlation_id"],
        }
        response["output_hash"] = payload_hash(response)

        persist_proposal_result(
            conn,
            proposal_id=proposal["proposal_id"],
            status="rejected",
            response_payload=response,
            output_hash=response["output_hash"],
            decision_reason=payload.get("reason"),
        )
        insert_decision(
            conn,
            proposal_id=proposal["proposal_id"],
            action="reject",
            correlation_id=payload["correlation_id"],
            reason=payload.get("reason"),
        )
        log_event(
            conn,
            tool_name="reject_proposed_transaction",
            correlation_id=payload["correlation_id"],
            input_hash=input_hash,
            output_hash=response["output_hash"],
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )
        return response
