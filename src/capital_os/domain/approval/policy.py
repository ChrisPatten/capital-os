from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from capital_os.config import get_settings
from capital_os.domain.ledger.invariants import normalize_amount


@dataclass(frozen=True)
class ApprovalPolicy:
    threshold_amount: Decimal



def load_approval_policy() -> ApprovalPolicy:
    settings = get_settings()
    threshold = normalize_amount(settings.approval_threshold_amount)
    if threshold < Decimal("0.0000"):
        raise ValueError("approval threshold must be non-negative")
    return ApprovalPolicy(threshold_amount=threshold)



def transaction_impact_amount(postings: list[dict]) -> Decimal:
    # Balanced bundles have equal total positive/negative legs.
    absolute_total = sum((abs(normalize_amount(posting["amount"])) for posting in postings), Decimal("0.0000"))
    return normalize_amount(absolute_total / Decimal("2"))
