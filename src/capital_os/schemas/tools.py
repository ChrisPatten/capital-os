from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PostingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    amount: Decimal
    currency: Literal["USD"]
    memo: str | None = None


class RecordTransactionBundleIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_system: str
    external_id: str
    date: datetime
    description: str
    postings: list[PostingIn] = Field(min_length=2)
    correlation_id: str


class RecordTransactionBundleOut(BaseModel):
    status: Literal["committed", "idempotent-replay"]
    transaction_id: str
    posting_ids: list[str]
    correlation_id: str
    output_hash: str


class RecordBalanceSnapshotIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_system: str
    account_id: str
    snapshot_date: date
    balance: Decimal
    currency: Literal["USD"]
    source_artifact_id: str | None = None
    correlation_id: str


class RecordBalanceSnapshotOut(BaseModel):
    status: Literal["recorded", "updated"]
    snapshot_id: str
    account_id: str
    snapshot_date: str
    correlation_id: str
    output_hash: str


class CreateOrUpdateObligationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_system: str
    name: str
    account_id: str
    cadence: Literal["monthly", "annual", "custom"]
    expected_amount: Decimal
    variability_flag: bool = False
    next_due_date: date
    metadata: dict = Field(default_factory=dict)
    correlation_id: str


class CreateOrUpdateObligationOut(BaseModel):
    status: Literal["created", "updated"]
    obligation_id: str
    correlation_id: str
    output_hash: str


class ComputeCapitalPostureIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    liquidity: Decimal
    fixed_burn: Decimal
    variable_burn: Decimal
    minimum_reserve: Decimal
    volatility_buffer: Decimal = Decimal("0.0000")
    correlation_id: str


class ComputeCapitalPostureOut(BaseModel):
    fixed_burn: Decimal
    variable_burn: Decimal
    volatility_buffer: Decimal
    reserve_target: Decimal
    liquidity: Decimal
    liquidity_surplus: Decimal
    reserve_ratio: Decimal
    risk_band: Literal["critical", "elevated", "guarded", "stable"]
    correlation_id: str
    output_hash: str
