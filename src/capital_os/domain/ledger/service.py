from __future__ import annotations

from time import perf_counter
import sqlite3
from datetime import datetime, timezone

from capital_os.domain.approval.policy import transaction_impact_amount
from capital_os.domain.approval.repository import (
    fetch_proposal_by_source_external,
    insert_proposal,
    persist_proposal_result,
)
from capital_os.domain.entities import DEFAULT_ENTITY_ID
from capital_os.domain.periods.service import enforce_period_write_constraints
from capital_os.domain.policy.service import evaluate_transaction_policy
from capital_os.db.session import transaction
from capital_os.domain.ledger.idempotency import resolve_transaction_idempotency
from capital_os.domain.ledger.invariants import InvariantError, ensure_balanced, normalize_amount
from capital_os.domain.ledger.repository import (
    find_duplicate_risk_matches,
    insert_transaction_bundle,
    save_transaction_response,
    upsert_balance_snapshot,
    upsert_obligation,
    fulfill_obligation as _repo_fulfill_obligation,
)
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash


def _as_utc_iso(value: object) -> str:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _proposal_transaction_payload(payload: dict) -> dict:
    postings = sorted(
        payload["postings"],
        key=lambda posting: (
            posting["account_id"],
            str(normalize_amount(posting["amount"])),
            posting.get("memo") or "",
        ),
    )
    normalized_postings = [
        {
            "account_id": posting["account_id"],
            "amount": str(normalize_amount(posting["amount"])),
            "currency": posting["currency"],
            "memo": posting.get("memo"),
        }
        for posting in postings
    ]
    return {
        "source_system": payload["source_system"],
        "external_id": payload["external_id"],
        "date": _as_utc_iso(payload["date"]),
        "description": payload["description"],
        "entity_id": payload.get("entity_id", DEFAULT_ENTITY_ID),
        "postings": normalized_postings,
    }


def _duplicate_risk_context(*, tx_payload: dict, duplicate_matches: list[dict]) -> dict:
    normalized_matches = []
    for match in duplicate_matches:
        normalized_postings = sorted(
            match["postings"],
            key=lambda posting: (
                posting["account_id"],
                str(normalize_amount(posting["amount"])),
                posting["posting_id"],
            ),
        )
        normalized_matches.append(
            {
                "match_reason": "same_account_date_amount",
                "transaction_id": match["transaction_id"],
                "source_system": match["source_system"],
                "external_id": match["external_id"],
                "date": _as_utc_iso(match["date"]),
                "description": match["description"],
                "correlation_id": match["correlation_id"],
                "entity_id": match.get("entity_id", DEFAULT_ENTITY_ID),
                "postings": [
                    {
                        "posting_id": posting["posting_id"],
                        "account_id": posting["account_id"],
                        "amount": str(normalize_amount(posting["amount"])),
                        "currency": posting["currency"],
                        "memo": posting.get("memo"),
                    }
                    for posting in normalized_postings
                ],
            }
        )
    normalized_matches.sort(key=lambda match: (match["date"], match["transaction_id"]))
    return {
        "match_reason": "same_account_date_amount",
        "proposed_transaction": _proposal_transaction_payload(tx_payload),
        "matched_transactions": normalized_matches,
    }


def _proposal_response_payload(
    proposal: dict,
    *,
    duplicate_context: dict | None = None,
) -> dict:
    response = dict(proposal.get("response_payload") or {})
    if response:
        return response

    response = {
        "status": "proposed",
        "proposal_id": proposal["proposal_id"],
        "correlation_id": proposal["correlation_id"],
        "approval_threshold_amount": str(normalize_amount(proposal["policy_threshold_amount"])),
        "impact_amount": str(normalize_amount(proposal["impact_amount"])),
        "matched_rule_id": proposal.get("matched_rule_id"),
        "required_approvals": int(proposal.get("required_approvals") or 1),
        "approvals_received": 0,
    }
    if duplicate_context is not None:
        response.update(duplicate_context)
    response["output_hash"] = payload_hash(response)
    return response


def record_transaction_bundle(payload: dict) -> dict:
    started = perf_counter()
    input_hash = payload_hash(payload)

    if any(p["currency"] != "USD" for p in payload["postings"]):
        raise InvariantError("Only USD is supported in phase 1")
    ensure_balanced(payload["postings"])
    impact_amount = transaction_impact_amount(payload["postings"])

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

            tx_payload = dict(payload)
            tx_payload.setdefault("entity_id", DEFAULT_ENTITY_ID)
            force_approval = enforce_period_write_constraints(conn, tx_payload)
            policy_decision = evaluate_transaction_policy(
                conn,
                payload=tx_payload,
                impact_amount=impact_amount,
                tool_name="record_transaction_bundle",
                force_approval=force_approval,
            )
            duplicate_matches = find_duplicate_risk_matches(
                conn,
                effective_date=tx_payload["date"],
                postings=tx_payload["postings"],
            )
            duplicate_approval_required = bool(duplicate_matches)

            if policy_decision.approval_required or duplicate_approval_required:
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
                        policy_threshold_amount=str(policy_decision.threshold_amount),
                        impact_amount=str(impact_amount),
                        request_payload=tx_payload,
                        entity_id=tx_payload.get("entity_id"),
                        matched_rule_id=policy_decision.matched_rule_id,
                        required_approvals=policy_decision.required_approvals,
                    )
                    proposal = fetch_proposal_by_source_external(
                        conn,
                        tool_name="record_transaction_bundle",
                        source_system=payload["source_system"],
                        external_id=payload["external_id"],
                    )
                    if not proposal:
                        raise InvariantError(f"proposal {proposal_id} was not persisted")

                duplicate_context = None
                if duplicate_approval_required:
                    duplicate_context = _duplicate_risk_context(
                        tx_payload=tx_payload,
                        duplicate_matches=duplicate_matches,
                    )

                response = _proposal_response_payload(proposal, duplicate_context=duplicate_context)
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

            tx_payload = dict(payload)
            tx_payload.setdefault("entity_id", DEFAULT_ENTITY_ID)
            duplicate_matches = find_duplicate_risk_matches(
                conn,
                effective_date=tx_payload["date"],
                postings=tx_payload["postings"],
            )
            duplicate_context = None
            if duplicate_matches:
                duplicate_context = _duplicate_risk_context(
                    tx_payload=tx_payload,
                    duplicate_matches=duplicate_matches,
                )

            response = _proposal_response_payload(proposal, duplicate_context=duplicate_context)
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
        obligation_id, status, active = upsert_obligation(conn, payload)
        response = {
            "status": status,
            "obligation_id": obligation_id,
            "active": active,
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


def fulfill_obligation(payload: dict) -> dict:
    started = perf_counter()
    input_hash = payload_hash(payload)
    with transaction() as conn:
        result = _repo_fulfill_obligation(conn, payload)
        response = {
            **result,
            "correlation_id": payload["correlation_id"],
        }
        output_hash = payload_hash(response)
        response["output_hash"] = output_hash
        log_event(
            conn,
            tool_name="fulfill_obligation",
            correlation_id=payload["correlation_id"],
            input_hash=input_hash,
            output_hash=output_hash,
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )
        return response
