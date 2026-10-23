from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal
from time import perf_counter

from capital_os.db.session import read_only_connection, transaction
from capital_os.domain.budget import repository as repo
from capital_os.domain.ledger.invariants import InvariantError
from capital_os.domain.query.pagination import decode_cursor_payload, encode_cursor
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash

_QUANT = Decimal("0.0001")
_BUCKET_ORDER = ("recurring", "debt", "annual", "discretionary", "savings")
# Exact monthly-equivalent factors; arithmetic stays in Decimal, quantized only at output.
_MONTHLY_FACTOR = {
    "monthly": Decimal(1),
    "biweekly": Decimal(26) / Decimal(12),
    "quarterly": Decimal(1) / Decimal(3),
    "annual": Decimal(1) / Decimal(12),
}


def _q(value: Decimal) -> Decimal:
    return value.quantize(_QUANT, rounding=ROUND_HALF_EVEN)


def monthly_equivalent(amount: Decimal, cadence: str) -> Decimal:
    if cadence == "biweekly":
        return amount * 26 / 12
    if cadence == "quarterly":
        return amount / 3
    if cadence == "annual":
        return amount / 12
    return amount


def upsert_budget_item(payload: dict) -> dict:
    """Versioned upsert keyed by item_key.

    Statuses: created (first version), versioned (superseded an active version),
    unchanged (identical active version, or deactivation requested with nothing active),
    deactivated (active version switched off). Deactivating an item_key that has never
    existed fails with InvariantError.
    """
    started = perf_counter()
    input_hash = payload_hash(payload)
    item_key = payload["item_key"]
    payload = {**payload, "entity_id": payload.get("entity_id") or "entity-default"}
    with transaction() as conn:
        account_id = payload.get("account_id")
        if account_id is not None and not repo.account_exists(conn, account_id):
            raise InvariantError(f"unknown account_id: {account_id}")

        current = repo.fetch_active_version(conn, item_key)
        if not payload.get("active", True):
            if current is not None:
                repo.deactivate_item(conn, current["item_id"])
                status, item_id, active = "deactivated", current["item_id"], False
            else:
                latest = repo.fetch_latest_version(conn, item_key)
                if latest is None:
                    raise InvariantError(f"unknown item_key: {item_key}")
                status, item_id, active = "unchanged", latest["item_id"], False
        elif current is not None and repo.normalized_content(current) == repo.normalized_content(payload):
            status, item_id, active = "unchanged", current["item_id"], True
        else:
            if current is not None:
                repo.deactivate_item(conn, current["item_id"])
                status = "versioned"
            else:
                status = "created" if not repo.has_any_version(conn, item_key) else "versioned"
            item_id = repo.insert_item(conn, payload)
            active = True

        response = {
            "status": status,
            "item_id": item_id,
            "item_key": item_key,
            "active": active,
            "correlation_id": payload["correlation_id"],
        }
        output_hash = payload_hash(response)
        response["output_hash"] = output_hash
        log_event(
            conn,
            tool_name="upsert_budget_item",
            correlation_id=payload["correlation_id"],
            input_hash=input_hash,
            output_hash=output_hash,
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )
        return response


def list_budget_items(payload: dict) -> dict:
    started = perf_counter()
    input_hash = payload_hash(payload)
    limit = payload.get("limit", 50)
    cursor_keys = None
    if payload.get("cursor"):
        cp = decode_cursor_payload(payload["cursor"], required_keys=("item_key", "effective_date", "item_id"))
        cursor_keys = {k: cp[k] for k in ("item_key", "effective_date", "item_id")}

    with read_only_connection() as conn:
        rows = repo.list_items_page(
            conn,
            limit=limit,
            cursor=cursor_keys,
            active_only=payload.get("active_only", True),
            direction=payload.get("direction"),
            bucket=payload.get("bucket"),
            account_id=payload.get("account_id"),
        )
    next_cursor = None
    if len(rows) > limit:
        tail = rows[limit - 1]
        rows = rows[:limit]
        next_cursor = encode_cursor(
            {"v": 1, "item_key": tail["item_key"], "effective_date": tail["effective_date"], "item_id": tail["item_id"]}
        )
    response = {"items": rows, "next_cursor": next_cursor, "correlation_id": payload["correlation_id"]}
    response["output_hash"] = payload_hash(response)
    _log_read("list_budget_items", payload["correlation_id"], input_hash, response["output_hash"], started)
    return response


def get_budget_summary(payload: dict) -> dict:
    started = perf_counter()
    input_hash = payload_hash({k: (str(v) if v is not None else None) for k, v in payload.items()})
    as_of = payload.get("as_of_date")
    with read_only_connection() as conn:
        rows = repo.fetch_summary_rows(
            conn,
            entity_id=payload.get("entity_id"),
            as_of_date=str(as_of) if as_of is not None else None,
        )

    take_home = Decimal(0)
    untracked = Decimal(0)
    bucket_totals = {b: Decimal(0) for b in _BUCKET_ORDER}
    per_account: dict[str, dict[str, Decimal]] = {}
    for row in rows:
        monthly = monthly_equivalent(row["amount"], row["cadence"])
        if row["direction"] == "inflow":
            take_home += monthly
            if row["account_id"] is None:
                untracked += monthly
        else:
            bucket_totals[row["bucket"]] += monthly
        if row["account_id"] is not None:
            acct = per_account.setdefault(row["account_id"], {"in": Decimal(0), "out": Decimal(0)})
            acct["in" if row["direction"] == "inflow" else "out"] += monthly

    total_outflows = sum(bucket_totals.values(), Decimal(0))
    buckets = [
        {
            "bucket": b,
            "monthly_amount": _q(bucket_totals[b]),
            "pct_of_take_home": _q(bucket_totals[b] / take_home * 100) if take_home else _q(Decimal(0)),
        }
        for b in _BUCKET_ORDER
    ]
    accounts = [
        {
            "account_id": account_id,
            "inflow_monthly": _q(v["in"]),
            "outflow_monthly": _q(v["out"]),
            "net_monthly": _q(v["in"] - v["out"]),
        }
        for account_id, v in sorted(per_account.items())
    ]
    response = {
        "take_home_monthly": _q(take_home),
        "untracked_inflows_monthly": _q(untracked),
        "buckets": buckets,
        "total_outflows_monthly": _q(total_outflows),
        "leftover_monthly": _q(take_home - untracked - total_outflows),
        "accounts": accounts,
        "item_count": len(rows),
        "correlation_id": payload["correlation_id"],
    }
    response["output_hash"] = payload_hash(response)
    _log_read("get_budget_summary", payload["correlation_id"], input_hash, response["output_hash"], started)
    return response


def _log_read(tool_name: str, correlation_id: str, input_hash: str, output_hash: str, started: float) -> None:
    with transaction() as conn:
        log_event(
            conn,
            tool_name=tool_name,
            correlation_id=correlation_id,
            input_hash=input_hash,
            output_hash=output_hash,
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )
