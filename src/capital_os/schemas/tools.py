from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from capital_os.domain.entities import DEFAULT_ENTITY_ID
from capital_os.domain.ledger.invariants import normalize_amount
from capital_os.domain.query.pagination import decode_cursor, decode_cursor_payload


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
    entity_id: str = DEFAULT_ENTITY_ID
    transaction_category: str | None = Field(default=None, min_length=1, max_length=64)
    risk_band: Literal["low", "medium", "high", "critical"] | None = None
    is_adjusting_entry: bool = False
    adjusting_reason_code: Literal["accrual", "reclass", "correction", "year_end", "other"] | None = None
    override_period_lock: bool = False
    override_reason: str | None = Field(default=None, max_length=256)
    correlation_id: str

    @model_validator(mode="after")
    def _validate_adjustments(self) -> "RecordTransactionBundleIn":
        if self.is_adjusting_entry and not self.adjusting_reason_code:
            raise ValueError("adjusting_reason_code is required when is_adjusting_entry=true")
        if not self.is_adjusting_entry and self.adjusting_reason_code is not None:
            raise ValueError("adjusting_reason_code must be null when is_adjusting_entry=false")
        if self.override_period_lock and not self.override_reason:
            raise ValueError("override_reason is required when override_period_lock=true")
        if not self.override_period_lock and self.override_reason is not None:
            raise ValueError("override_reason must be null when override_period_lock=false")
        return self


class RecordTransactionBundleOut(BaseModel):
    status: Literal["committed", "idempotent-replay", "proposed", "rejected"]
    transaction_id: str | None = None
    posting_ids: list[str] = Field(default_factory=list)
    proposal_id: str | None = None
    approval_threshold_amount: Decimal | None = None
    impact_amount: Decimal | None = None
    matched_rule_id: str | None = None
    required_approvals: int | None = None
    approvals_received: int | None = None
    correlation_id: str
    output_hash: str


class ApproveProposedTransactionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    approver_id: str | None = Field(default=None, min_length=1, max_length=128)
    reason: str | None = None
    correlation_id: str


class ApproveProposedTransactionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["committed", "proposed"]
    proposal_id: str
    transaction_id: str | None = None
    posting_ids: list[str] = Field(default_factory=list)
    required_approvals: int | None = None
    approvals_received: int | None = None
    correlation_id: str
    output_hash: str


class RejectProposedTransactionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    approver_id: str | None = Field(default=None, min_length=1, max_length=128)
    reason: str | None = None
    correlation_id: str


class RejectProposedTransactionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["rejected"]
    proposal_id: str
    reason: str | None = None
    correlation_id: str
    output_hash: str


class ClosePeriodIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_key: str = Field(pattern=r"^\d{4}-\d{2}$")
    entity_id: str = DEFAULT_ENTITY_ID
    actor_id: str | None = Field(default=None, min_length=1, max_length=128)
    correlation_id: str

    @field_validator("period_key")
    @classmethod
    def _validate_period_key_month(cls, value: str) -> str:
        month = int(value.split("-")[1])
        if month < 1 or month > 12:
            raise ValueError("period_key month must be in 01..12")
        return value


class ClosePeriodOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["closed", "already_closed", "already_locked"]
    period_key: str
    entity_id: str
    state: Literal["closed", "locked"]
    closed_at: str | None = None
    locked_at: str | None = None
    correlation_id: str
    output_hash: str


class LockPeriodIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_key: str = Field(pattern=r"^\d{4}-\d{2}$")
    entity_id: str = DEFAULT_ENTITY_ID
    actor_id: str | None = Field(default=None, min_length=1, max_length=128)
    correlation_id: str

    @field_validator("period_key")
    @classmethod
    def _validate_period_key_month(cls, value: str) -> str:
        month = int(value.split("-")[1])
        if month < 1 or month > 12:
            raise ValueError("period_key month must be in 01..12")
        return value


class LockPeriodOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["locked", "already_locked"]
    period_key: str
    entity_id: str
    state: Literal["locked"]
    closed_at: str | None = None
    locked_at: str | None = None
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
    entity_id: str = DEFAULT_ENTITY_ID
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
    entity_id: str = DEFAULT_ENTITY_ID
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


class ListAccountsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=50, ge=1, le=500)
    cursor: str | None = None
    correlation_id: str

    @field_validator("cursor")
    @classmethod
    def _validate_cursor(cls, value: str | None) -> str | None:
        if value is None:
            return value
        decode_cursor(value)
        return value


class AccountNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    code: str
    name: str
    account_type: Literal["asset", "liability", "equity", "income", "expense"]
    parent_account_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class ListAccountsOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accounts: list[AccountNode]
    next_cursor: str | None = None
    correlation_id: str
    output_hash: str


class TreeAccountNode(AccountNode):
    model_config = ConfigDict(extra="forbid")

    children: list["TreeAccountNode"] = Field(default_factory=list)


class GetAccountTreeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root_account_id: str | None = None
    correlation_id: str


class GetAccountTreeOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root_account_id: str | None = None
    accounts: list[TreeAccountNode]
    correlation_id: str
    output_hash: str


class GetAccountBalancesIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of_date: date
    source_policy: Literal["ledger_only", "snapshot_only", "best_available"] | None = None
    correlation_id: str


class AccountBalanceRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    code: str
    name: str
    account_type: Literal["asset", "liability", "equity", "income", "expense"]
    balance: Decimal | None = None
    currency: Literal["USD"]
    source_used: Literal["ledger", "snapshot", "none"]
    ledger_balance: Decimal
    snapshot_balance: Decimal | None = None
    snapshot_date: date | None = None


class GetAccountBalancesOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of_date: date
    source_policy: Literal["ledger_only", "snapshot_only", "best_available"]
    balances: list[AccountBalanceRow]
    correlation_id: str
    output_hash: str


class ListTransactionsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=50, ge=1, le=500)
    cursor: str | None = None
    correlation_id: str

    @field_validator("cursor")
    @classmethod
    def _validate_cursor(cls, value: str | None) -> str | None:
        if value is None:
            return value
        decode_cursor_payload(value, required_keys=("transaction_date", "transaction_id"))
        return value


class TransactionListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: str
    source_system: str
    external_id: str
    transaction_date: datetime
    description: str
    correlation_id: str
    entity_id: str
    created_at: datetime
    posting_count: int
    gross_posting_amount: Decimal
    currency: Literal["USD"]


class ListTransactionsOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transactions: list[TransactionListItem]
    next_cursor: str | None = None
    correlation_id: str
    output_hash: str


class TransactionPostingOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    posting_id: str
    account_id: str
    account_code: str
    account_name: str
    amount: Decimal
    currency: Literal["USD"]
    memo: str | None = None


class GetTransactionByExternalIdIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_system: str
    external_id: str
    correlation_id: str


class TransactionWithPostingsOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: str
    source_system: str
    external_id: str
    transaction_date: datetime
    description: str
    correlation_id: str
    entity_id: str
    created_at: datetime
    postings: list[TransactionPostingOut]


class GetTransactionByExternalIdOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction: TransactionWithPostingsOut | None = None
    correlation_id: str
    output_hash: str


class ListObligationsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=50, ge=1, le=500)
    cursor: str | None = None
    active_only: bool = True
    correlation_id: str

    @field_validator("cursor")
    @classmethod
    def _validate_cursor(cls, value: str | None) -> str | None:
        if value is None:
            return value
        decode_cursor_payload(value, required_keys=("next_due_date", "obligation_id"))
        return value


class ObligationListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    obligation_id: str
    source_system: str
    name: str
    account_id: str
    cadence: Literal["monthly", "annual", "custom"]
    expected_amount: Decimal
    variability_flag: bool
    next_due_date: date
    metadata: dict = Field(default_factory=dict)
    active: bool
    entity_id: str
    created_at: datetime
    updated_at: datetime


class ListObligationsOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    obligations: list[ObligationListItem]
    next_cursor: str | None = None
    correlation_id: str
    output_hash: str


class ListProposalsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=50, ge=1, le=500)
    cursor: str | None = None
    status: Literal["proposed", "rejected", "committed"] | None = None
    correlation_id: str

    @field_validator("cursor")
    @classmethod
    def _validate_cursor(cls, value: str | None) -> str | None:
        if value is None:
            return value
        decode_cursor_payload(value, required_keys=("created_at", "proposal_id"))
        return value


class ProposalListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    tool_name: str
    source_system: str
    external_id: str
    correlation_id: str
    status: Literal["proposed", "rejected", "committed"]
    policy_threshold_amount: Decimal
    impact_amount: Decimal
    matched_rule_id: str | None = None
    required_approvals: int
    entity_id: str
    created_at: datetime
    updated_at: datetime


class ListProposalsOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposals: list[ProposalListItem]
    next_cursor: str | None = None
    correlation_id: str
    output_hash: str


class ProposalDecisionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str
    action: Literal["approve", "reject"]
    correlation_id: str
    reason: str | None = None
    approver_id: str | None = None
    created_at: datetime


class GetProposalIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    correlation_id: str


class ProposalDetailsOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    tool_name: str
    source_system: str
    external_id: str
    correlation_id: str
    input_hash: str
    status: Literal["proposed", "rejected", "committed"]
    policy_threshold_amount: Decimal
    impact_amount: Decimal
    request_payload: dict | None = None
    response_payload: dict | None = None
    output_hash: str | None = None
    decision_reason: str | None = None
    approved_transaction_id: str | None = None
    matched_rule_id: str | None = None
    required_approvals: int
    entity_id: str
    created_at: datetime
    updated_at: datetime
    decisions: list[ProposalDecisionOut]


class GetProposalOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal: ProposalDetailsOut | None = None
    correlation_id: str
    output_hash: str


class ConfigRuleOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    priority: int
    tool_name: str | None = None
    entity_id: str | None = None
    transaction_category: str | None = None
    risk_band: str | None = None
    velocity_limit_count: int | None = None
    velocity_window_seconds: int | None = None
    threshold_amount: Decimal
    required_approvals: int
    active: bool
    metadata: dict = Field(default_factory=dict)
    created_at: datetime


class GetConfigIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correlation_id: str


class GetConfigOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runtime: dict
    policy_rules: list[ConfigRuleOut]
    correlation_id: str
    output_hash: str


class ProposeConfigChangeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_system: str
    external_id: str
    scope: Literal["runtime_settings", "policy_rules"]
    change_payload: dict = Field(default_factory=dict)
    correlation_id: str


class ProposeConfigChangeOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["proposed", "idempotent-replay"]
    proposal_id: str
    required_approvals: int
    approvals_received: int
    correlation_id: str
    output_hash: str


class ApproveConfigChangeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    approver_id: str | None = Field(default=None, min_length=1, max_length=128)
    reason: str | None = None
    correlation_id: str


class ApproveConfigChangeOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["applied", "already_applied", "rejected"]
    proposal_id: str
    approvals_received: int
    required_approvals: int
    applied_change: dict | None = None
    correlation_id: str
    output_hash: str


class ReconcileSuggestedPosting(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    amount: Decimal
    currency: Literal["USD"]
    memo: str | None = None


class ReconcileSuggestedAdjustmentBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["proposed"]
    auto_commit: Literal[False]
    source_system: str
    external_id: str
    date: date
    description: str
    postings: list[ReconcileSuggestedPosting] = Field(min_length=2)


class ReconcileAccountIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    as_of_date: date
    method: Literal["ledger_only", "snapshot_only", "best_available"]
    correlation_id: str


class ReconcileAccountOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "account_not_found"]
    account_id: str
    as_of_date: date
    method: Literal["ledger_only", "snapshot_only", "best_available"]
    source_used: Literal["ledger", "snapshot", "none"]
    ledger_balance: Decimal | None = None
    snapshot_balance: Decimal | None = None
    snapshot_date: date | None = None
    delta: Decimal | None = None
    suggested_adjustment_bundle: ReconcileSuggestedAdjustmentBundle | None = None
    correlation_id: str
    output_hash: str


TreeAccountNode.model_rebuild()
