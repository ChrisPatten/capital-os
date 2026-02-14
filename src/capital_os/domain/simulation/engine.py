from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from capital_os.domain.ledger.invariants import normalize_amount
from capital_os.observability.hashing import payload_hash


def _add_months(source: date, months: int) -> date:
    year = source.year + ((source.month - 1 + months) // 12)
    month = ((source.month - 1 + months) % 12) + 1
    day = source.day
    if month == 2 and day > 28:
        day = 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28
    elif month in {4, 6, 9, 11} and day > 30:
        day = 30
    return date(year, month, day)


class SimulationSpend(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spend_id: str
    amount: Decimal
    type: Literal["one_time", "recurring"]
    spend_date: date | None = None
    start_date: date | None = None
    cadence: Literal["monthly", "weekly"] = "monthly"
    occurrences: int = Field(default=1, ge=1)

    @field_validator("amount", mode="before")
    @classmethod
    def _normalize_amount(cls, value: Decimal | str) -> Decimal:
        normalized = normalize_amount(value)
        if normalized < Decimal("0.0000"):
            raise ValueError("amount must be non-negative")
        return normalized

    @model_validator(mode="after")
    def _enforce_branch_fields(self):
        if self.type == "one_time":
            if self.spend_date is None:
                raise ValueError("spend_date is required for one_time spends")
            if self.start_date is not None:
                raise ValueError("start_date is not allowed for one_time spends")
            if self.occurrences != 1:
                raise ValueError("occurrences must be 1 for one_time spends")
        else:
            if self.start_date is None:
                raise ValueError("start_date is required for recurring spends")
            if self.spend_date is not None:
                raise ValueError("spend_date is not allowed for recurring spends")
        return self


class SimulationInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_liquidity: Decimal
    start_date: date
    horizon_periods: int = Field(ge=1, le=120)
    spends: list[SimulationSpend] = Field(default_factory=list)

    @field_validator("starting_liquidity", mode="before")
    @classmethod
    def _normalize_starting_liquidity(cls, value: Decimal | str) -> Decimal:
        return normalize_amount(value)

    @field_validator("spends")
    @classmethod
    def _ensure_unique_spend_ids(cls, spends: list[SimulationSpend]) -> list[SimulationSpend]:
        seen: set[str] = set()
        for spend in spends:
            if spend.spend_id in seen:
                raise ValueError("spend_id values must be unique")
            seen.add(spend.spend_id)
        return spends


class SimulationPeriod(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_index: int
    period_start: date
    period_end: date
    one_time_total: Decimal
    recurring_total: Decimal
    total_spend: Decimal
    ending_liquidity: Decimal

    @field_validator("one_time_total", "recurring_total", "total_spend", "ending_liquidity", mode="before")
    @classmethod
    def _normalize_amounts(cls, value: Decimal | str) -> Decimal:
        return normalize_amount(value)


class SimulationProjection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_liquidity: Decimal
    periods: list[SimulationPeriod]

    @field_validator("starting_liquidity", mode="before")
    @classmethod
    def _normalize_starting_liquidity(cls, value: Decimal | str) -> Decimal:
        return normalize_amount(value)


def _recurring_dates(spend: SimulationSpend) -> list[date]:
    if spend.type != "recurring" or spend.start_date is None:
        return []

    dates: list[date] = []
    for idx in range(spend.occurrences):
        if spend.cadence == "monthly":
            dates.append(_add_months(spend.start_date, idx))
        else:
            dates.append(spend.start_date + timedelta(days=7 * idx))
    return dates


def compute_simulation_projection(inputs: SimulationInputs) -> SimulationProjection:
    sorted_spends = sorted(inputs.spends, key=lambda spend: (spend.spend_id, spend.type))
    recurring_schedules = {spend.spend_id: _recurring_dates(spend) for spend in sorted_spends}

    current_liquidity = inputs.starting_liquidity
    periods: list[SimulationPeriod] = []
    for period_index in range(inputs.horizon_periods):
        period_start = _add_months(inputs.start_date, period_index)
        period_end = _add_months(period_start, 1) - timedelta(days=1)

        one_time_total = Decimal("0.0000")
        recurring_total = Decimal("0.0000")
        for spend in sorted_spends:
            if spend.type == "one_time" and spend.spend_date is not None:
                if period_start <= spend.spend_date <= period_end:
                    one_time_total = normalize_amount(one_time_total + spend.amount)
            elif spend.type == "recurring":
                for occurrence_date in recurring_schedules[spend.spend_id]:
                    if period_start <= occurrence_date <= period_end:
                        recurring_total = normalize_amount(recurring_total + spend.amount)

        total_spend = normalize_amount(one_time_total + recurring_total)
        current_liquidity = normalize_amount(current_liquidity - total_spend)
        periods.append(
            SimulationPeriod(
                period_index=period_index,
                period_start=period_start,
                period_end=period_end,
                one_time_total=one_time_total,
                recurring_total=recurring_total,
                total_spend=total_spend,
                ending_liquidity=current_liquidity,
            )
        )

    return SimulationProjection(starting_liquidity=inputs.starting_liquidity, periods=periods)


def compute_simulation_projection_with_hash(inputs: SimulationInputs) -> dict:
    projection = compute_simulation_projection(inputs)
    payload = {
        "starting_liquidity": f"{projection.starting_liquidity:.4f}",
        "periods": [
            {
                "period_index": period.period_index,
                "period_start": period.period_start.isoformat(),
                "period_end": period.period_end.isoformat(),
                "one_time_total": f"{period.one_time_total:.4f}",
                "recurring_total": f"{period.recurring_total:.4f}",
                "total_spend": f"{period.total_spend:.4f}",
                "ending_liquidity": f"{period.ending_liquidity:.4f}",
            }
            for period in projection.periods
        ],
    }
    payload["output_hash"] = payload_hash(payload)
    return payload
