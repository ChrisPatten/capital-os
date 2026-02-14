from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from capital_os.domain.ledger.invariants import normalize_amount
from capital_os.observability.hashing import payload_hash


RiskBand = Literal["critical", "elevated", "guarded", "stable"]


class PostureComputationInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    liquidity: Decimal
    fixed_burn: Decimal
    variable_burn: Decimal
    minimum_reserve: Decimal
    volatility_buffer: Decimal

    @field_validator(
        "liquidity", "fixed_burn", "variable_burn", "minimum_reserve", "volatility_buffer", mode="before"
    )
    @classmethod
    def _normalize_money(cls, value: Decimal | str) -> Decimal:
        return normalize_amount(value)

    @field_validator("fixed_burn", "variable_burn", "minimum_reserve", "volatility_buffer")
    @classmethod
    def _ensure_non_negative(cls, value: Decimal) -> Decimal:
        if value < Decimal("0.0000"):
            raise ValueError("burn and reserve inputs must be non-negative")
        return value


class PostureMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixed_burn: Decimal
    variable_burn: Decimal
    volatility_buffer: Decimal
    reserve_target: Decimal
    liquidity: Decimal
    liquidity_surplus: Decimal
    reserve_ratio: Decimal
    risk_band: RiskBand

    @field_validator(
        "fixed_burn",
        "variable_burn",
        "volatility_buffer",
        "reserve_target",
        "liquidity",
        "liquidity_surplus",
        "reserve_ratio",
        mode="before",
    )
    @classmethod
    def _normalize_money(cls, value: Decimal | str) -> Decimal:
        return normalize_amount(value)


def _derive_risk_band(reserve_ratio: Decimal) -> RiskBand:
    if reserve_ratio < Decimal("0.5000"):
        return "critical"
    if reserve_ratio < Decimal("1.0000"):
        return "elevated"
    if reserve_ratio < Decimal("1.5000"):
        return "guarded"
    return "stable"


def compute_posture_metrics(inputs: PostureComputationInputs) -> PostureMetrics:
    reserve_target = normalize_amount(inputs.minimum_reserve + inputs.volatility_buffer)
    liquidity_surplus = normalize_amount(inputs.liquidity - reserve_target)

    if reserve_target == Decimal("0.0000"):
        reserve_ratio = Decimal("0.0000")
    else:
        reserve_ratio = normalize_amount(inputs.liquidity / reserve_target)

    return PostureMetrics(
        fixed_burn=inputs.fixed_burn,
        variable_burn=inputs.variable_burn,
        volatility_buffer=inputs.volatility_buffer,
        reserve_target=reserve_target,
        liquidity=inputs.liquidity,
        liquidity_surplus=liquidity_surplus,
        reserve_ratio=reserve_ratio,
        risk_band=_derive_risk_band(reserve_ratio),
    )


def compute_posture_metrics_with_hash(inputs: PostureComputationInputs) -> dict:
    metrics = compute_posture_metrics(inputs)
    payload = {
        "fixed_burn": f"{metrics.fixed_burn:.4f}",
        "variable_burn": f"{metrics.variable_burn:.4f}",
        "volatility_buffer": f"{metrics.volatility_buffer:.4f}",
        "reserve_target": f"{metrics.reserve_target:.4f}",
        "liquidity": f"{metrics.liquidity:.4f}",
        "liquidity_surplus": f"{metrics.liquidity_surplus:.4f}",
        "reserve_ratio": f"{metrics.reserve_ratio:.4f}",
        "risk_band": metrics.risk_band,
        "explanation": {
            "contributing_balances": [
                {"name": "liquidity", "amount": f"{metrics.liquidity:.4f}"},
                {"name": "fixed_burn", "amount": f"{metrics.fixed_burn:.4f}"},
                {"name": "variable_burn", "amount": f"{metrics.variable_burn:.4f}"},
            ],
            "reserve_assumptions": {
                "minimum_reserve": f"{inputs.minimum_reserve:.4f}",
                "volatility_buffer": f"{metrics.volatility_buffer:.4f}",
                "reserve_target": f"{metrics.reserve_target:.4f}",
            },
        },
    }
    payload["output_hash"] = payload_hash(payload)
    return payload
