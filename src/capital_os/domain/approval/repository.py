from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from capital_os.domain.entities import DEFAULT_ENTITY_ID
from capital_os.observability.hashing import canonical_json


ALLOWED_PROPOSAL_STATUSES = {"proposed", "rejected", "committed"}



def _decode_json(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    return json.loads(value)



def _row_to_proposal(row) -> dict[str, Any] | None:
    if not row:
        return None

    proposal = dict(row)
    proposal["request_payload"] = _decode_json(proposal.get("request_payload"))
    proposal["response_payload"] = _decode_json(proposal.get("response_payload"))
    return proposal



def fetch_proposal_by_source_external(conn, *, tool_name: str, source_system: str, external_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT *
        FROM approval_proposals
        WHERE tool_name=? AND source_system=? AND external_id=?
        """,
        (tool_name, source_system, external_id),
    ).fetchone()
    return _row_to_proposal(row)



def fetch_proposal_by_id(conn, proposal_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT *
        FROM approval_proposals
        WHERE proposal_id=?
        """,
        (proposal_id,),
    ).fetchone()
    return _row_to_proposal(row)



def insert_proposal(
    conn,
    *,
    tool_name: str,
    source_system: str,
    external_id: str,
    correlation_id: str,
    input_hash: str,
    policy_threshold_amount: str,
    impact_amount: str,
    request_payload: dict[str, Any],
    entity_id: str | None = None,
) -> str:
    proposal_id = str(uuid4())
    conn.execute(
        """
        INSERT INTO approval_proposals (
          proposal_id, tool_name, source_system, external_id, correlation_id,
          input_hash, policy_threshold_amount, impact_amount, request_payload, status, entity_id
        ) VALUES (?,?,?,?,?,?,?,?,?,'proposed',?)
        """,
        (
            proposal_id,
            tool_name,
            source_system,
            external_id,
            correlation_id,
            input_hash,
            policy_threshold_amount,
            impact_amount,
            canonical_json(request_payload),
            entity_id or DEFAULT_ENTITY_ID,
        ),
    )
    return proposal_id



def persist_proposal_result(
    conn,
    *,
    proposal_id: str,
    status: str,
    response_payload: dict[str, Any],
    output_hash: str,
    decision_reason: str | None = None,
    approved_transaction_id: str | None = None,
) -> None:
    if status not in ALLOWED_PROPOSAL_STATUSES:
        raise ValueError(f"invalid proposal status: {status}")

    conn.execute(
        """
        UPDATE approval_proposals
        SET status=?, response_payload=?, output_hash=?, decision_reason=?, approved_transaction_id=?
        WHERE proposal_id=?
        """,
        (
            status,
            canonical_json(response_payload),
            output_hash,
            decision_reason,
            approved_transaction_id,
            proposal_id,
        ),
    )



def insert_decision(conn, *, proposal_id: str, action: str, correlation_id: str, reason: str | None) -> str:
    decision_id = str(uuid4())
    conn.execute(
        """
        INSERT INTO approval_decisions (decision_id, proposal_id, action, correlation_id, reason)
        VALUES (?,?,?,?,?)
        """,
        (decision_id, proposal_id, action, correlation_id, reason),
    )
    return decision_id
