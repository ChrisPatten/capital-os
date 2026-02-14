from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class Posting:
    account_id: str
    amount: Decimal
    currency: str
    memo: str | None = None


@dataclass(frozen=True)
class BalanceSnapshot:
    account_id: str
    snapshot_date: date
    balance: Decimal
    currency: str
    source_system: str


@dataclass(frozen=True)
class Obligation:
    obligation_id: str
    name: str
    account_id: str
    cadence: str
    expected_amount: Decimal
    variability_flag: bool
    next_due_date: date
    metadata: dict
    active: bool
    updated_at: datetime
