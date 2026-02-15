from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
import sqlite3

from capital_os.domain.approval.policy import load_approval_policy, transaction_impact_amount
from capital_os.domain.approval.repository import (
    fetch_proposal_by_source_external,
    insert_proposal,
    persist_proposal_result,
)
from capital_os.db.session import transaction
from capital_os.domain.ledger.idempotency import resolve_transaction_idempotency
from capital_os.domain.ledger.invariants import InvariantError, ensure_balanced, normalize_amount
from capital_os.domain.ledger.repository import (
    insert_transaction_bundle,
    save_transaction_response,
    upsert_balance_snapshot,
    upsert_obligation,
)
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash


def _proposal_response_payload(proposal: dict) -> dict:
    response = dict(proposal.get("response_payload") or {})
    if response:
        return response

    response = {
        "status": "proposed",
        "proposal_id": proposal["proposal_id"],
        "correlation_id": proposal["correlation_id"],
        "approval_threshold_amount": str(normalize_amount(proposal["policy_threshold_amount"])),
        "impact_amount": str(normalize_amount(proposal["impact_amount"])),
    }
    response["output_hash"] = payload_hash(response)
    return response


def record_transaction_bundle(payload: dict) -> dict:
    started = perf_counter()
    input_hash = payload_hash(payload)

    if any(p["currency"] != "USD" for p in payload["postings"]):
        raise InvariantError("Only USD is supported in phase 1")
    ensure_balanced(payload["postings"])
    policy = load_approval_policy()
    impact_amount = transaction_impact_amount(payload["postings"])
    approval_required = impact_amount > policy.threshold_amount

    try:
        with transaction() as conn:
            replay = resolve_transaction_idempotency(conn, payload["source_system"], payload["external_id"])
            if replay:
                output_hash = replay.get("output_hash") or payload_hash(replay)
                log_event(
                    conn,
                    tool_name="record_transaction_bundle",
                    correlation_id=payload["correlation_id"],
                    input_hash=input_hash,
                    output_hash=output_hash,
                    duration_ms=int((perf_counter() - started) * 1000),
                    status="ok",
                )
                replay["output_hash"] = output_hash
                return replay

            if approval_required:
                proposal = fetch_proposal_by_source_external(
                    conn,
                    tool_name="record_transaction_bundle",
                    source_system=payload["source_system"],
                    external_id=payload["external_id"],
                )
                if not proposal:
                    proposal_id = insert_proposal(
                        conn,
                        tool_name="record_transaction_bundle",
                        source_system=payload["source_system"],
                        external_id=payload["external_id"],
                        correlation_id=payload["correlation_id"],
                        input_hash=input_hash,
                        policy_threshold_amount=str(policy.threshold_amount),
                        impact_amount=str(impact_amount),
                        request_payload=payload,
                        entity_id=payload.get("entity_id"),
                    )
                    proposal = fetch_proposal_by_source_external(
                        conn,
                        tool_name="record_transaction_bundle",
                        source_system=payload["source_system"],
                        external_id=payload["external_id"],
                    )
                    if not proposal:
                        raise InvariantError(f"proposal {proposal_id} was not persisted")

                response = _proposal_response_payload(proposal)
                if not proposal.get("response_payload"):
                    persist_proposal_result(
                        conn,
                        proposal_id=proposal["proposal_id"],
                        status="proposed",
                        response_payload=response,
                        output_hash=response["output_hash"],
                    )

                log_event(
                    conn,
                    tool_name="record_transaction_bundle",
                    correlation_id=payload["correlation_id"],
                    input_hash=input_hash,
                    output_hash=response["output_hash"],
                    duration_ms=int((perf_counter() - started) * 1000),
                    status="ok",
                )
                return response

            tx_payload = dict(payload)
            tx_payload["input_hash"] = input_hash
            transaction_id, posting_ids = insert_transaction_bundle(conn, tx_payload)
            response = {
                "status": "committed",
                "transaction_id": transaction_id,
                "posting_ids": posting_ids,
                "correlation_id": payload["correlation_id"],
            }
            output_hash = payload_hash(response)
            response["output_hash"] = output_hash
            save_transaction_response(conn, transaction_id, response, output_hash)
            log_event(
                conn,
                tool_name="record_transaction_bundle",
                correlation_id=payload["correlation_id"],
                input_hash=input_hash,
                output_hash=output_hash,
                duration_ms=int((perf_counter() - started) * 1000),
                status="ok",
            )
            return response
    except sqlite3.IntegrityError:
        with transaction() as conn:
            replay = resolve_transaction_idempotency(conn, payload["source_system"], payload["external_id"])
            if replay:
                output_hash = replay.get("output_hash") or payload_hash(replay)
                replay["status"] = "idempotent-replay"
                replay["output_hash"] = output_hash
                log_event(
                    conn,
                    tool_name="record_transaction_bundle",
                    correlation_id=payload["correlation_id"],
                    input_hash=input_hash,
                    output_hash=output_hash,
                    duration_ms=int((perf_counter() - started) * 1000),
                    status="ok",
                )
                return replay

            proposal = fetch_proposal_by_source_external(
                conn,
                tool_name="record_transaction_bundle",
                source_system=payload["source_system"],
                external_id=payload["external_id"],
            )
            if not proposal:
                raise

            response = _proposal_response_payload(proposal)
            if not proposal.get("response_payload"):
                persist_proposal_result(
                    conn,
                    proposal_id=proposal["proposal_id"],
                    status="proposed",
                    response_payload=response,
                    output_hash=response["output_hash"],
                )
            log_event(
                conn,
                tool_name="record_transaction_bundle",
                correlation_id=payload["correlation_id"],
                input_hash=input_hash,
                output_hash=response["output_hash"],
                duration_ms=int((perf_counter() - started) * 1000),
                status="ok",
            )
            return response


def record_balance_snapshot(payload: dict) -> dict:
    started = perf_counter()
    input_hash = payload_hash(payload)
    with transaction() as conn:
        snapshot_id, status = upsert_balance_snapshot(conn, payload)
        response = {
            "status": status,
            "snapshot_id": snapshot_id,
            "account_id": payload["account_id"],
            "snapshot_date": str(payload["snapshot_date"]),
            "correlation_id": payload["correlation_id"],
        }
        output_hash = payload_hash(response)
        response["output_hash"] = output_hash
        log_event(
            conn,
            tool_name="record_balance_snapshot",
            correlation_id=payload["correlation_id"],
            input_hash=input_hash,
            output_hash=output_hash,
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )
        return response


def create_or_update_obligation(payload: dict) -> dict:
    started = perf_counter()
    input_hash = payload_hash(payload)
    with transaction() as conn:
        obligation_id, status = upsert_obligation(conn, payload)
        response = {
            "status": status,
            "obligation_id": obligation_id,
            "correlation_id": payload["correlation_id"],
        }
        output_hash = payload_hash(response)
        response["output_hash"] = output_hash
        log_event(
            conn,
            tool_name="create_or_update_obligation",
            correlation_id=payload["correlation_id"],
            input_hash=input_hash,
            output_hash=output_hash,
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )
        return response
