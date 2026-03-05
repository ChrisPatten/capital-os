from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from time import perf_counter

from capital_os.domain.approval.repository import (
    fetch_proposal_by_source_external,
    insert_proposal,
    persist_proposal_result,
)
from capital_os.db.session import transaction
from capital_os.domain.entities import DEFAULT_ENTITY_ID
from capital_os.domain.ledger.repository import (
    close_account_identifier_history,
    create_account,
    fetch_active_account_identifier_history,
    fetch_account_profile,
    insert_account_identifier_history,
    list_accounts_subtree,
    update_account_profile_fields,
)
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash


def create_account_entry(payload: dict) -> dict:
    started = perf_counter()
    input_hash = payload_hash(payload)
    try:
        with transaction() as conn:
            entity_id = payload.get("entity_id", DEFAULT_ENTITY_ID)
            parent_account_id = payload.get("parent_account_id")

            if parent_account_id is not None:
                row = conn.execute(
                    "SELECT account_id FROM accounts WHERE account_id = ?",
                    (parent_account_id,),
                ).fetchone()
                if row is None:
                    raise ValueError(f"parent_account_id '{parent_account_id}' does not exist")

            if entity_id != DEFAULT_ENTITY_ID:
                row = conn.execute(
                    "SELECT entity_id FROM entities WHERE entity_id = ?",
                    (entity_id,),
                ).fetchone()
                if row is None:
                    raise ValueError(f"entity_id '{entity_id}' does not exist")

            account_id = create_account(conn, payload)

            response = {
                "account_id": account_id,
                "status": "committed",
                "correlation_id": payload["correlation_id"],
            }
            output_hash = payload_hash(response)
            response["output_hash"] = output_hash

            log_event(
                conn,
                tool_name="create_account",
                correlation_id=payload["correlation_id"],
                input_hash=input_hash,
                output_hash=output_hash,
                duration_ms=int((perf_counter() - started) * 1000),
                status="ok",
            )
            return response
    except sqlite3.IntegrityError as exc:
        msg = str(exc).lower()
        if "unique" in msg and "code" in msg:
            raise ValueError(f"account code '{payload.get('code')}' already exists") from exc
        if "cycle" in msg or "hierarchy" in msg:
            raise ValueError("account hierarchy cycle detected") from exc
        raise ValueError(str(exc)) from exc


def update_account_metadata(payload: dict) -> dict:
    started = perf_counter()
    input_hash = payload_hash(payload)
    account_id = payload["account_id"]
    patch = payload["metadata"]

    with transaction() as conn:
        row = conn.execute(
            "SELECT metadata FROM accounts WHERE account_id = ?",
            (account_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"account_id '{account_id}' does not exist")

        current = json.loads(row["metadata"]) if row["metadata"] else {}

        # RFC 7396 merge-patch: overwrite provided keys, remove null keys, preserve unmentioned
        for key, value in patch.items():
            if value is None:
                current.pop(key, None)
            else:
                current[key] = value

        conn.execute(
            "UPDATE accounts SET metadata = ? WHERE account_id = ?",
            (json.dumps(current, separators=(",", ":"), sort_keys=True), account_id),
        )

        response = {
            "account_id": account_id,
            "metadata": current,
            "status": "committed",
            "correlation_id": payload["correlation_id"],
        }
        output_hash = payload_hash(response)
        response["output_hash"] = output_hash

        log_event(
            conn,
            tool_name="update_account_metadata",
            correlation_id=payload["correlation_id"],
            input_hash=input_hash,
            output_hash=output_hash,
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )
        return response


def list_account_subtree(root_account_id: str | None = None) -> dict:
    with transaction() as conn:
        rows = list_accounts_subtree(conn, root_account_id)
    return {"accounts": rows}


def update_account_profile(payload: dict) -> dict:
    started = perf_counter()
    input_hash = payload_hash(payload)

    with transaction() as conn:
        proposal = fetch_proposal_by_source_external(
            conn,
            tool_name="update_account_profile",
            source_system=payload["source_system"],
            external_id=payload["external_id"],
        )
        if proposal is not None and proposal.get("response_payload"):
            response = dict(proposal["response_payload"])
            output_hash = response.get("output_hash") or payload_hash(response)
            response["output_hash"] = output_hash
            log_event(
                conn,
                tool_name="update_account_profile",
                correlation_id=payload["correlation_id"],
                input_hash=input_hash,
                output_hash=output_hash,
                duration_ms=int((perf_counter() - started) * 1000),
                status="ok",
            )
            return response

        proposal_id: str
        try:
            proposal_id = insert_proposal(
                conn,
                tool_name="update_account_profile",
                source_system=payload["source_system"],
                external_id=payload["external_id"],
                correlation_id=payload["correlation_id"],
                input_hash=input_hash,
                policy_threshold_amount="0.0000",
                impact_amount="0.0000",
                request_payload=payload,
                matched_rule_id=None,
                required_approvals=1,
            )
        except sqlite3.IntegrityError:
            replay = fetch_proposal_by_source_external(
                conn,
                tool_name="update_account_profile",
                source_system=payload["source_system"],
                external_id=payload["external_id"],
            )
            if replay is None or not replay.get("response_payload"):
                raise
            response = dict(replay["response_payload"])
            output_hash = response.get("output_hash") or payload_hash(response)
            response["output_hash"] = output_hash
            log_event(
                conn,
                tool_name="update_account_profile",
                correlation_id=payload["correlation_id"],
                input_hash=input_hash,
                output_hash=output_hash,
                duration_ms=int((perf_counter() - started) * 1000),
                status="ok",
            )
            return response

        current = fetch_account_profile(conn, payload["account_id"])
        if current is None:
            raise ValueError(f"account_id '{payload['account_id']}' does not exist")

        display_name = current["display_name"]
        if "display_name" in payload:
            display_name = payload["display_name"]

        metadata = dict(current["metadata"])
        if "institution_name" in payload:
            if payload["institution_name"] is None:
                metadata.pop("institution_name", None)
            else:
                metadata["institution_name"] = payload["institution_name"]
        if "institution_suffix" in payload:
            if payload["institution_suffix"] is None:
                metadata.pop("institution_suffix", None)
            else:
                metadata["institution_suffix"] = payload["institution_suffix"]

        update_account_profile_fields(
            conn,
            account_id=payload["account_id"],
            display_name=display_name,
            metadata=metadata,
        )

        active_identifier = fetch_active_account_identifier_history(
            conn,
            account_id=payload["account_id"],
            source_system=payload["source_system"],
        )
        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        next_suffix = metadata.get("institution_suffix")

        if active_identifier is None:
            insert_account_identifier_history(
                conn,
                account_id=payload["account_id"],
                source_system=payload["source_system"],
                external_id=payload["external_id"],
                institution_suffix=next_suffix,
                correlation_id=payload["correlation_id"],
                valid_from=now_utc,
            )
        else:
            active_external_id = active_identifier["external_id"]
            active_suffix = active_identifier["institution_suffix"]
            if active_external_id != payload["external_id"] or active_suffix != next_suffix:
                close_account_identifier_history(
                    conn,
                    history_id=active_identifier["history_id"],
                    valid_to=now_utc,
                )
                insert_account_identifier_history(
                    conn,
                    account_id=payload["account_id"],
                    source_system=payload["source_system"],
                    external_id=payload["external_id"],
                    institution_suffix=next_suffix,
                    correlation_id=payload["correlation_id"],
                    valid_from=now_utc,
                )

        response = {
            "account_id": payload["account_id"],
            "display_name": display_name,
            "institution_name": metadata.get("institution_name"),
            "institution_suffix": metadata.get("institution_suffix"),
            "status": "committed",
            "correlation_id": payload["correlation_id"],
        }
        output_hash = payload_hash(response)
        response["output_hash"] = output_hash

        persist_proposal_result(
            conn,
            proposal_id=proposal_id,
            status="committed",
            response_payload=response,
            output_hash=output_hash,
        )

        log_event(
            conn,
            tool_name="update_account_profile",
            correlation_id=payload["correlation_id"],
            input_hash=input_hash,
            output_hash=output_hash,
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )
        return response
