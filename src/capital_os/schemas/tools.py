from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from capital_os.domain.ledger.invariants import normalize_amount


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


class PostureContributingBalance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Literal["liquidity", "fixed_burn", "variable_burn"]
    amount: Decimal


class PostureReserveAssumptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_reserve: Decimal
    volatility_buffer: Decimal
    reserve_target: Decimal


class PostureExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contributing_balances: list[PostureContributingBalance] = Field(min_length=3, max_length=3)
    reserve_assumptions: PostureReserveAssumptions


class ComputeCapitalPostureOut(BaseModel):
    fixed_burn: Decimal
    variable_burn: Decimal
    volatility_buffer: Decimal
    reserve_target: Decimal
    liquidity: Decimal
    liquidity_surplus: Decimal
    reserve_ratio: Decimal
    risk_band: Literal["critical", "elevated", "guarded", "stable"]
    explanation: PostureExplanation
    correlation_id: str
    output_hash: str


class SimulateSpendItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spend_id: str
    amount: Decimal
    type: Literal["one_time", "recurring"]
    spend_date: date | None = None
    start_date: date | None = None
    cadence: Literal["monthly", "weekly"] = "monthly"
    occurrences: int = Field(default=1, ge=1)


class SimulateSpendIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_liquidity: Decimal
    start_date: date
    horizon_periods: int = Field(ge=1, le=120)
    spends: list[SimulateSpendItemIn] = Field(default_factory=list)
    correlation_id: str


class SimulateSpendPeriodOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_index: int
    period_start: date
    period_end: date
    one_time_total: Decimal
    recurring_total: Decimal
    total_spend: Decimal
    ending_liquidity: Decimal


class SimulateSpendOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_liquidity: Decimal
    periods: list[SimulateSpendPeriodOut]
    correlation_id: str
    output_hash: str


class AnalyzeDebtLiabilityIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    liability_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$")
    current_balance: Decimal
    apr: Decimal
    minimum_payment: Decimal

    @field_validator("liability_id")
    @classmethod
    def _reject_secret_like_ids(cls, value: str) -> str:
        lowered = value.lower()
        blocked_tokens = ("secret", "token", "password", "api_key", "apikey")
        if any(token in lowered for token in blocked_tokens):
            raise ValueError("liability_id contains disallowed secret-like text")
        return value

    @field_validator("current_balance", "apr", "minimum_payment", mode="before")
    @classmethod
    def _normalize_decimal(cls, value: Decimal | str) -> Decimal:
        normalized = normalize_amount(value)
        if normalized < Decimal("0.0000"):
            raise ValueError("value must be non-negative")
        return normalized


class AnalyzeDebtIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    liabilities: list[AnalyzeDebtLiabilityIn] = Field(min_length=1)
    optional_payoff_amount: Decimal | None = None
    reserve_floor: Decimal = Decimal("0.0000")
    correlation_id: str

    @field_validator("optional_payoff_amount", "reserve_floor", mode="before")
    @classmethod
    def _normalize_optional_decimal(cls, value: Decimal | str | None) -> Decimal | None:
        if value is None:
            return None
        normalized = normalize_amount(value)
        if normalized < Decimal("0.0000"):
            raise ValueError("value must be non-negative")
        return normalized

    @field_validator("liabilities")
    @classmethod
    def _validate_unique_liability_ids(
        cls, liabilities: list[AnalyzeDebtLiabilityIn]
    ) -> list[AnalyzeDebtLiabilityIn]:
        ids = [liability.liability_id for liability in liabilities]
        if len(set(ids)) != len(ids):
            raise ValueError("liability_id values must be unique")
        return liabilities

    @model_validator(mode="after")
    def _normalize_defaults(self) -> "AnalyzeDebtIn":
        if self.optional_payoff_amount is not None and self.optional_payoff_amount < Decimal("0.0000"):
            raise ValueError("optional_payoff_amount must be non-negative")
        if self.reserve_floor < Decimal("0.0000"):
            raise ValueError("reserve_floor must be non-negative")
        return self


class AnalyzeDebtScoreExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    annual_interest_cost: Decimal
    cashflow_pressure: Decimal
    payoff_readiness: Decimal


class AnalyzeDebtLiabilityOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int
    liability_id: str
    current_balance: Decimal
    apr: Decimal
    minimum_payment: Decimal
    score: Decimal
    estimated_annual_interest: Decimal
    payoff_applied: Decimal
    post_payoff_balance: Decimal
    interest_saved: Decimal
    cashflow_freed: Decimal
    reserve_impact: Decimal
    explanation: AnalyzeDebtScoreExplanation


class AnalyzeDebtOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    optional_payoff_amount: Decimal | None
    reserve_floor: Decimal
    total_interest_saved: Decimal
    total_cashflow_freed: Decimal
    total_reserve_impact: Decimal
    ranked_liabilities: list[AnalyzeDebtLiabilityOut]
    correlation_id: str
    output_hash: str
