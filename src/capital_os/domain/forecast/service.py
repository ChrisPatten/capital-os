from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from time import perf_counter

from capital_os.db.session import read_only_connection, transaction
from capital_os.domain.dates import add_months, next_business_day
from capital_os.domain.forecast import repository as repo
from capital_os.domain.ledger.invariants import InvariantError
from capital_os.observability.event_log import log_event
from capital_os.observability.hashing import payload_hash

_QUANT = Decimal("0.0001")
_CADENCE_MONTHS = {"quarterly": 3, "annual": 12}


def _q(value: Decimal) -> Decimal:
    return value.quantize(_QUANT, rounding=ROUND_HALF_EVEN)


def _nominal_dates(item: dict, lo: date, hi: date) -> list[date] | None:
    """Nominal (pre-business-day-shift) occurrences in [lo, hi]; None when the item lacks its anchor/day."""
    cadence = item["cadence"]
    out: list[date] = []
    if cadence == "monthly":
        if item["day_of_month"] is None:
            return None
        months = (hi.year * 12 + hi.month) - (lo.year * 12 + lo.month)
        first = date(lo.year, lo.month, 1)
        for m in range(months + 1):
            d = add_months(first, m, day=item["day_of_month"])
            if lo <= d <= hi:
                out.append(d)
        return out
    if item["anchor_date"] is None:
        return None
    anchor = date.fromisoformat(item["anchor_date"])
    if cadence == "biweekly":
        k = -((anchor - lo).days // 14)  # ceil((lo - anchor) / 14)
        d = anchor + timedelta(days=14 * k)
        while d <= hi:
            out.append(d)
            d += timedelta(days=14)
        return out
    step = _CADENCE_MONTHS[cadence]
    approx = ((lo.year * 12 + lo.month) - (anchor.year * 12 + anchor.month)) // step - 1
    k = approx
    while True:
        d = add_months(anchor, step * k)
        if d > hi:
            break
        if d >= lo:
            out.append(d)
        k += 1
    return out


def _generate_events(
    items: list[dict], obligations: list[dict], lo_excl: date, hi_incl: date
) -> tuple[list[dict], list[dict]]:
    """Events whose business-day-adjusted date falls in (lo_excl, hi_incl].

    Occurrences are generated from the nominal date and filtered on the adjusted date; the nominal
    window is widened by 2 days on the low side because a weekend shift moves a date forward by <= 2.
    """
    events: list[dict] = []
    unscheduled: list[dict] = []
    nominal_lo = lo_excl - timedelta(days=1)
    for item in items:
        nominal = _nominal_dates(item, nominal_lo, hi_incl)
        if nominal is None:
            unscheduled.append({"source_id": item["item_id"], "name": item["name"], "reason": "missing_schedule"})
            continue
        effective = date.fromisoformat(item["effective_date"])
        sign = Decimal(1) if item["direction"] == "inflow" else Decimal(-1)
        for d in nominal:
            if d < effective:
                continue
            adjusted = next_business_day(d)
            if lo_excl < adjusted <= hi_incl:
                events.append(
                    {
                        "date": adjusted,
                        "name": item["name"],
                        "kind": "budget_item",
                        "source_id": item["item_id"],
                        "direction": item["direction"],
                        "amount": sign * item["amount"],
                    }
                )
    for ob in obligations:
        adjusted = next_business_day(date.fromisoformat(ob["next_due_date"]))
        if lo_excl < adjusted <= hi_incl:
            events.append(
                {
                    "date": adjusted,
                    "name": ob["name"],
                    "kind": "obligation",
                    "source_id": ob["obligation_id"],
                    "direction": "outflow",
                    "amount": -ob["amount"],
                }
            )
    # Same date: inflows first, then outflows by name, then source id.
    events.sort(key=lambda e: (e["date"], 0 if e["direction"] == "inflow" else 1, e["name"], e["source_id"]))
    return events, unscheduled


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def forecast_cash(payload: dict) -> dict:
    started = perf_counter()
    input_hash = payload_hash({k: (str(v) if v is not None else None) for k, v in payload.items()})
    account_id = payload["account_id"]
    as_of: date = payload["as_of_date"]
    days: int = payload["days"]
    entity_id = payload.get("entity_id") or "entity-default"
    include_unposted = bool(payload.get("include_unposted", False))
    threshold = payload.get("threshold")
    end_date = as_of + timedelta(days=days)

    with read_only_connection() as conn:
        if not repo.account_exists(conn, account_id):
            raise InvariantError(f"unknown account_id: {account_id}")
        snapshot = None
        if payload.get("starting_balance") is None:
            snapshot = repo.fetch_latest_snapshot(
                conn, account_id=account_id, entity_id=entity_id, on_or_before=as_of.isoformat()
            )
            if snapshot is None:
                raise InvariantError(
                    f"no balance snapshot on or before {as_of.isoformat()} for account {account_id}; "
                    "provide starting_balance"
                )
        items = repo.fetch_budget_items(conn, account_id=account_id, entity_id=entity_id)
        obligations = repo.fetch_one_time_obligations(conn, account_id=account_id, entity_id=entity_id)

    unposted: list[dict] | None = None
    if snapshot is None:
        balance = Decimal(payload["starting_balance"])
        start = {"date": as_of, "balance": _q(balance), "source": "explicit", "snapshot_date": None}
        unscheduled: list[dict] = []
    else:
        snap_date = date.fromisoformat(snapshot["snapshot_date"])
        balance = snapshot["balance"]
        unscheduled = []
        if include_unposted and snap_date < as_of:
            unposted_events, unscheduled = _generate_events(items, obligations, snap_date, as_of)
            unposted = []
            for ev in unposted_events:
                balance += ev["amount"]
                unposted.append({**ev, "amount": _q(ev["amount"]), "balance_after": _q(balance)})
        start = {"date": as_of, "balance": _q(balance), "source": "snapshot", "snapshot_date": snap_date}

    events, unscheduled_fwd = _generate_events(items, obligations, as_of, end_date)
    unscheduled = unscheduled or unscheduled_fwd
    start_balance = balance
    ledger: list[dict] = []
    for ev in events:
        balance += ev["amount"]
        ledger.append({**ev, "amount": _q(ev["amount"]), "balance_after": balance})

    # Monthly minimums over calendar months touched by (as_of, end_date].
    first_day = as_of + timedelta(days=1)
    n_months = (end_date.year * 12 + end_date.month) - (first_day.year * 12 + first_day.month)
    by_month: dict[str, list[dict]] = {}
    for ev in ledger:
        by_month.setdefault(_month_key(ev["date"]), []).append(ev)
    monthly: list[dict] = []
    carried = start_balance
    for m in range(n_months + 1):
        key = _month_key(add_months(date(first_day.year, first_day.month, 1), m))
        month_events = by_month.get(key, [])
        if not month_events:
            monthly.append({"month": key, "min_balance": _q(carried), "date": None, "item": None})
            continue
        low = month_events[0]
        for ev in month_events[1:]:
            if ev["balance_after"] < low["balance_after"]:
                low = ev
        monthly.append({"month": key, "min_balance": _q(low["balance_after"]), "date": low["date"], "item": low["name"]})
        carried = month_events[-1]["balance_after"]

    overall = {"balance": _q(start_balance), "date": None, "item": None}
    low_exact = start_balance
    for ev in ledger:
        if ev["balance_after"] < low_exact:
            low_exact = ev["balance_after"]
            overall = {"balance": _q(low_exact), "date": ev["date"], "item": ev["name"]}

    below = None if threshold is None else bool(low_exact < Decimal(threshold))
    out_events = [{**ev, "balance_after": _q(ev["balance_after"])} for ev in ledger]

    response: dict = {
        "account_id": account_id,
        "as_of_date": as_of,
        "end_date": end_date,
        "start": start,
        "unposted_events": unposted,
        "events": out_events,
        "monthly_minimums": monthly,
        "overall_minimum": overall,
        "threshold": _q(Decimal(threshold)) if threshold is not None else None,
        "below_threshold": below,
        "unscheduled_items": unscheduled,
        "correlation_id": payload["correlation_id"],
    }
    response["output_hash"] = payload_hash(_jsonable(response))
    _log_read(payload["correlation_id"], input_hash, response["output_hash"], started)
    return response


def _jsonable(value):
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, date):
        return value.isoformat()
    return value


def _log_read(correlation_id: str, input_hash: str, output_hash: str, started: float) -> None:
    with transaction() as conn:
        log_event(
            conn,
            tool_name="forecast_cash",
            correlation_id=correlation_id,
            input_hash=input_hash,
            output_hash=output_hash,
            duration_ms=int((perf_counter() - started) * 1000),
            status="ok",
        )
