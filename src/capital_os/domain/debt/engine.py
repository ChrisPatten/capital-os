from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from capital_os.domain.ledger.invariants import normalize_amount
from capital_os.observability.hashing import payload_hash


class DebtLiability(BaseModel):
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


class DebtAnalysisInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    liabilities: list[DebtLiability] = Field(min_length=1)
    optional_payoff_amount: Decimal | None = None
    reserve_floor: Decimal = Decimal("0.0000")

    @field_validator("optional_payoff_amount", "reserve_floor", mode="before")
    @classmethod
    def _normalize_decimal(cls, value: Decimal | str | None) -> Decimal | None:
        if value is None:
            return None
        normalized = normalize_amount(value)
        if normalized < Decimal("0.0000"):
            raise ValueError("value must be non-negative")
        return normalized

    @field_validator("liabilities")
    @classmethod
    def _validate_unique_liability_ids(cls, liabilities: list[DebtLiability]) -> list[DebtLiability]:
        ids = [liability.liability_id for liability in liabilities]
        if len(ids) != len(set(ids)):
            raise ValueError("liability_id values must be unique")
        return liabilities

    @model_validator(mode="after")
    def _validate_non_negative_values(self) -> "DebtAnalysisInputs":
        if self.reserve_floor < Decimal("0.0000"):
            raise ValueError("reserve_floor must be non-negative")
        if self.optional_payoff_amount is not None and self.optional_payoff_amount < Decimal("0.0000"):
            raise ValueError("optional_payoff_amount must be non-negative")
        return self


class DebtScoreExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    annual_interest_cost: Decimal
    cashflow_pressure: Decimal
    payoff_readiness: Decimal

    @field_validator("annual_interest_cost", "cashflow_pressure", "payoff_readiness", mode="before")
    @classmethod
    def _normalize_decimal(cls, value: Decimal | str) -> Decimal:
        return normalize_amount(value)


class RankedLiability(BaseModel):
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
    explanation: DebtScoreExplanation

    @field_validator(
        "current_balance",
        "apr",
        "minimum_payment",
        "score",
        "estimated_annual_interest",
        "payoff_applied",
        "post_payoff_balance",
        "interest_saved",
        "cashflow_freed",
        "reserve_impact",
        mode="before",
    )
    @classmethod
    def _normalize_decimal(cls, value: Decimal | str) -> Decimal:
        return normalize_amount(value)


class DebtAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    optional_payoff_amount: Decimal | None
    reserve_floor: Decimal
    total_interest_saved: Decimal
    total_cashflow_freed: Decimal
    total_reserve_impact: Decimal
    ranked_liabilities: list[RankedLiability]

    @field_validator(
        "optional_payoff_amount",
        "reserve_floor",
        "total_interest_saved",
        "total_cashflow_freed",
        "total_reserve_impact",
        mode="before",
    )
    @classmethod
    def _normalize_result_decimal(cls, value: Decimal | str | None) -> Decimal | None:
        if value is None:
            return None
        return normalize_amount(value)


def _estimated_annual_interest(liability: DebtLiability) -> Decimal:
    return normalize_amount(liability.current_balance * liability.apr / Decimal("100.0000"))


def _payoff_readiness(liability: DebtLiability, payoff_amount: Decimal | None) -> Decimal:
    if payoff_amount is None or payoff_amount == Decimal("0.0000"):
        return Decimal("0.0000")
    if liability.current_balance == Decimal("0.0000"):
        return Decimal("1.0000")
    ratio = payoff_amount / liability.current_balance
    if ratio > Decimal("1.0000"):
        ratio = Decimal("1.0000")
    return normalize_amount(ratio)


def _score_liability(liability: DebtLiability, payoff_amount: Decimal | None) -> tuple[Decimal, DebtScoreExplanation]:
    annual_interest = _estimated_annual_interest(liability)
    cashflow = liability.minimum_payment
    readiness = _payoff_readiness(liability, payoff_amount)
    score = normalize_amount(annual_interest + cashflow + (readiness * Decimal("100.0000")))
    return score, DebtScoreExplanation(
        annual_interest_cost=annual_interest,
        cashflow_pressure=cashflow,
        payoff_readiness=readiness,
    )


def analyze_liabilities(inputs: DebtAnalysisInputs) -> DebtAnalysisResult:
    scored: list[tuple[DebtLiability, Decimal, DebtScoreExplanation]] = []
    for liability in inputs.liabilities:
        score, explanation = _score_liability(liability, inputs.optional_payoff_amount)
        scored.append((liability, score, explanation))

    scored.sort(
        key=lambda row: (
            -row[1],
            -row[0].apr,
            -row[0].minimum_payment,
            row[0].liability_id,
        )
    )

    remaining_payoff = inputs.optional_payoff_amount or Decimal("0.0000")
    total_interest_saved = Decimal("0.0000")
    total_cashflow_freed = Decimal("0.0000")
    total_reserve_impact = Decimal("0.0000")
    ranked_liabilities: list[RankedLiability] = []

    for rank, (liability, score, explanation) in enumerate(scored, start=1):
        payoff_applied = min(remaining_payoff, liability.current_balance)
        post_payoff_balance = normalize_amount(liability.current_balance - payoff_applied)
        interest_saved = normalize_amount(payoff_applied * liability.apr / Decimal("100.0000"))
        cashflow_freed = liability.minimum_payment if post_payoff_balance == Decimal("0.0000") else Decimal("0.0000")
        reserve_impact = normalize_amount(-payoff_applied)

        remaining_payoff = normalize_amount(remaining_payoff - payoff_applied)
        total_interest_saved = normalize_amount(total_interest_saved + interest_saved)
        total_cashflow_freed = normalize_amount(total_cashflow_freed + cashflow_freed)
        total_reserve_impact = normalize_amount(total_reserve_impact + reserve_impact)

        ranked_liabilities.append(
            RankedLiability(
                rank=rank,
                liability_id=liability.liability_id,
                current_balance=liability.current_balance,
                apr=liability.apr,
                minimum_payment=liability.minimum_payment,
                score=score,
                estimated_annual_interest=_estimated_annual_interest(liability),
                payoff_applied=payoff_applied,
                post_payoff_balance=post_payoff_balance,
                interest_saved=interest_saved,
                cashflow_freed=cashflow_freed,
                reserve_impact=reserve_impact,
                explanation=explanation,
            )
        )

    return DebtAnalysisResult(
        optional_payoff_amount=inputs.optional_payoff_amount,
        reserve_floor=inputs.reserve_floor,
        total_interest_saved=total_interest_saved,
        total_cashflow_freed=total_cashflow_freed,
        total_reserve_impact=total_reserve_impact,
        ranked_liabilities=ranked_liabilities,
    )


def analyze_liabilities_with_hash(inputs: DebtAnalysisInputs) -> dict:
    result = analyze_liabilities(inputs)
    payload = {
        "optional_payoff_amount": (
            f"{result.optional_payoff_amount:.4f}" if result.optional_payoff_amount is not None else None
        ),
        "reserve_floor": f"{result.reserve_floor:.4f}",
        "total_interest_saved": f"{result.total_interest_saved:.4f}",
        "total_cashflow_freed": f"{result.total_cashflow_freed:.4f}",
        "total_reserve_impact": f"{result.total_reserve_impact:.4f}",
        "ranked_liabilities": [
            {
                "rank": ranked.rank,
                "liability_id": ranked.liability_id,
                "current_balance": f"{ranked.current_balance:.4f}",
                "apr": f"{ranked.apr:.4f}",
                "minimum_payment": f"{ranked.minimum_payment:.4f}",
                "score": f"{ranked.score:.4f}",
                "estimated_annual_interest": f"{ranked.estimated_annual_interest:.4f}",
                "payoff_applied": f"{ranked.payoff_applied:.4f}",
                "post_payoff_balance": f"{ranked.post_payoff_balance:.4f}",
                "interest_saved": f"{ranked.interest_saved:.4f}",
                "cashflow_freed": f"{ranked.cashflow_freed:.4f}",
                "reserve_impact": f"{ranked.reserve_impact:.4f}",
                "explanation": {
                    "annual_interest_cost": f"{ranked.explanation.annual_interest_cost:.4f}",
                    "cashflow_pressure": f"{ranked.explanation.cashflow_pressure:.4f}",
                    "payoff_readiness": f"{ranked.explanation.payoff_readiness:.4f}",
                },
            }
            for ranked in result.ranked_liabilities
        ],
    }
    payload["output_hash"] = payload_hash(payload)
    return payload
