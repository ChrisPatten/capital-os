from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from capital_os.domain.ledger.invariants import normalize_amount


class BurnAnalysisWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    window_start: datetime
    window_end: datetime

    @field_validator("window_start", "window_end")
    @classmethod
    def _normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamps must include timezone information")
        normalized = value.astimezone(UTC).replace(tzinfo=UTC)
        return normalized.replace(microsecond=normalized.microsecond)

    @model_validator(mode="after")
    def _check_range(self) -> "BurnAnalysisWindow":
        if self.window_start >= self.window_end:
            raise ValueError("burn analysis window_start must be before window_end")
        return self


class ReservePolicyParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_reserve_usd: Decimal
    volatility_buffer_usd: Decimal = Decimal("0.0000")

    @field_validator("minimum_reserve_usd", "volatility_buffer_usd", mode="before")
    @classmethod
    def _normalize_money(cls, value: Decimal | str) -> Decimal:
        return normalize_amount(value)


class PostureInputSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    liquidity_account_ids: list[str] = Field(min_length=1)
    burn_analysis_window: BurnAnalysisWindow
    reserve_policy: ReservePolicyParameters
    as_of: datetime
    currency: Literal["USD"] = "USD"

    @field_validator("as_of")
    @classmethod
    def _normalize_as_of(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must include timezone information")
        normalized = value.astimezone(UTC).replace(tzinfo=UTC)
        return normalized.replace(microsecond=normalized.microsecond)

    @field_validator("liquidity_account_ids")
    @classmethod
    def _validate_unique_liquidity_accounts(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("liquidity_account_ids contains duplicates")
        return value


class SelectedAccount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    code: str
    name: str
    account_type: str


class PostureInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    liquidity_account_ids: list[str]
    liquidity_accounts: list[SelectedAccount]
    burn_analysis_window: BurnAnalysisWindow
    reserve_policy: ReservePolicyParameters
    as_of: datetime
    currency: Literal["USD"]
