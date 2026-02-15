from __future__ import annotations

from decimal import Decimal

from capital_os.db.session import read_only_connection
from capital_os.domain.ledger.invariants import normalize_amount
from capital_os.domain.ledger.repository import fetch_account_balance_context


def _format_amount(value: Decimal) -> str:
    return str(normalize_amount(value))


def _suggested_adjustment_bundle(
    *,
    account_id: str,
    as_of_date: str,
    method: str,
    delta: Decimal,
) -> dict:
    normalized_delta = normalize_amount(delta)
    return {
        "status": "proposed",
        "auto_commit": False,
        "source_system": "capital-os-reconciliation",
        "external_id": (
            f"reconcile:{account_id}:{as_of_date}:{method}:{_format_amount(normalized_delta)}"
        ),
        "date": as_of_date,
        "description": f"Suggested reconciliation adjustment for account {account_id}",
        "postings": [
            {
                "account_id": account_id,
                "amount": _format_amount(normalized_delta),
                "currency": "USD",
                "memo": "Apply reconciliation delta to target account",
            },
            {
                "account_id": "__OFFSET_ACCOUNT_REQUIRED__",
                "amount": _format_amount(-normalized_delta),
                "currency": "USD",
                "memo": "Select balancing account before recording",
            },
        ],
    }


def reconcile_account(payload: dict) -> dict:
    account_id = payload["account_id"]
    as_of_date = str(payload["as_of_date"])
    method = payload["method"]

    with read_only_connection() as conn:
        context = fetch_account_balance_context(conn, account_id=account_id, as_of_date=as_of_date)

    if context is None:
        return {
            "status": "account_not_found",
            "account_id": account_id,
            "as_of_date": as_of_date,
            "method": method,
            "ledger_balance": None,
            "snapshot_balance": None,
            "snapshot_date": None,
            "delta": None,
            "suggested_adjustment_bundle": None,
            "source_used": "none",
        }

    ledger_balance = normalize_amount(context["ledger_balance"] or 0)
    snapshot_balance = (
        normalize_amount(context["snapshot_balance"]) if context["snapshot_balance"] is not None else None
    )
    delta = normalize_amount(snapshot_balance - ledger_balance) if snapshot_balance is not None else None

    source_used = "ledger"
    if method == "snapshot_only":
        source_used = "snapshot" if snapshot_balance is not None else "none"
    elif method == "best_available":
        source_used = "snapshot" if snapshot_balance is not None else "ledger"

    should_suggest = method in {"snapshot_only", "best_available"} and snapshot_balance is not None
    suggestion = None
    if should_suggest and delta != Decimal("0.0000"):
        suggestion = _suggested_adjustment_bundle(
            account_id=account_id,
            as_of_date=as_of_date,
            method=method,
            delta=delta,
        )

    return {
        "status": "ok",
        "account_id": account_id,
        "as_of_date": as_of_date,
        "method": method,
        "ledger_balance": _format_amount(ledger_balance),
        "snapshot_balance": _format_amount(snapshot_balance) if snapshot_balance is not None else None,
        "snapshot_date": context["snapshot_date"],
        "delta": _format_amount(delta) if delta is not None else None,
        "suggested_adjustment_bundle": suggestion,
        "source_used": source_used,
    }
