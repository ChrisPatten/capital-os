from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from capital_os.domain.approval.policy import load_approval_policy
from capital_os.domain.entities import DEFAULT_ENTITY_ID
from capital_os.domain.ledger.invariants import normalize_amount


@dataclass(frozen=True)
class PolicyDecision:
    approval_required: bool
    threshold_amount: Decimal
    impact_amount: Decimal
    required_approvals: int
    matched_rule_id: str | None


@dataclass(frozen=True)
class PolicyRule:
    rule_id: str
    priority: int
    tool_name: str | None
    entity_id: str | None
    transaction_category: str | None
    risk_band: str | None
    velocity_limit_count: int | None
    velocity_window_seconds: int | None
    threshold_amount: Decimal
    required_approvals: int


def _parse_dt(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _load_active_rules(conn) -> list[PolicyRule]:
    rows = conn.execute(
        """
        SELECT
          rule_id,
          priority,
          tool_name,
          entity_id,
          transaction_category,
          risk_band,
          velocity_limit_count,
          velocity_window_seconds,
          threshold_amount,
          required_approvals
        FROM policy_rules
        WHERE active = 1
        ORDER BY priority ASC, rule_id ASC
        """
    ).fetchall()

    rules: list[PolicyRule] = []
    for row in rows:
        rules.append(
            PolicyRule(
                rule_id=row["rule_id"],
                priority=row["priority"],
                tool_name=row["tool_name"],
                entity_id=row["entity_id"],
                transaction_category=row["transaction_category"],
                risk_band=row["risk_band"],
                velocity_limit_count=row["velocity_limit_count"],
                velocity_window_seconds=row["velocity_window_seconds"],
                threshold_amount=normalize_amount(row["threshold_amount"]),
                required_approvals=max(1, int(row["required_approvals"])),
            )
        )
    return rules


def _velocity_match(conn, *, rule: PolicyRule, payload: dict) -> bool:
    if rule.velocity_limit_count is None or rule.velocity_window_seconds is None:
        return True

    tx_date = _parse_dt(payload["date"])
    window_start = tx_date - timedelta(seconds=rule.velocity_window_seconds)

    window_start_iso = window_start.isoformat().replace("+00:00", "Z")
    tx_date_iso = tx_date.isoformat().replace("+00:00", "Z")
    observed_count = conn.execute(
        """
        SELECT COUNT(*) AS c
        FROM ledger_transactions
        WHERE source_system = ?
          AND entity_id = ?
          AND datetime(transaction_date) >= datetime(?)
          AND datetime(transaction_date) <= datetime(?)
        """,
        (
            payload["source_system"],
            payload.get("entity_id", DEFAULT_ENTITY_ID),
            window_start_iso,
            tx_date_iso,
        ),
    ).fetchone()["c"]
    if int(observed_count) == 0:
        observed_count = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM ledger_transactions
            WHERE source_system = ? AND entity_id = ?
            """,
            (
                payload["source_system"],
                payload.get("entity_id", DEFAULT_ENTITY_ID),
            ),
        ).fetchone()["c"]

    return int(observed_count) >= rule.velocity_limit_count


def _rule_matches(conn, *, rule: PolicyRule, payload: dict, tool_name: str) -> bool:
    if rule.tool_name and rule.tool_name != tool_name:
        return False
    if rule.entity_id and rule.entity_id != payload.get("entity_id", DEFAULT_ENTITY_ID):
        return False
    if rule.transaction_category and rule.transaction_category != payload.get("transaction_category"):
        return False
    if rule.risk_band and rule.risk_band != payload.get("risk_band"):
        return False
    return _velocity_match(conn, rule=rule, payload=payload)


def evaluate_transaction_policy(
    conn,
    *,
    payload: dict,
    impact_amount: Decimal,
    tool_name: str,
    force_approval: bool = False,
) -> PolicyDecision:
    fallback = load_approval_policy()
    selected_threshold = fallback.threshold_amount
    required_approvals = 1
    matched_rule_id: str | None = None
    selected_rule: PolicyRule | None = None

    for rule in _load_active_rules(conn):
        if _rule_matches(conn, rule=rule, payload=payload, tool_name=tool_name):
            selected_threshold = rule.threshold_amount
            required_approvals = rule.required_approvals
            matched_rule_id = rule.rule_id
            selected_rule = rule
            break

    velocity_forced = selected_rule is not None and selected_rule.velocity_limit_count is not None
    approval_required = force_approval or velocity_forced or impact_amount > selected_threshold
    return PolicyDecision(
        approval_required=approval_required,
        threshold_amount=selected_threshold,
        impact_amount=normalize_amount(impact_amount),
        required_approvals=required_approvals,
        matched_rule_id=matched_rule_id,
    )
