from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from capital_os.domain.posture.models import (
    BurnAnalysisWindow,
    PostureInputSelection,
    ReservePolicyParameters,
)


def test_reserve_policy_money_normalizes_to_4dp():
    policy = ReservePolicyParameters(
        minimum_reserve_usd=Decimal("1000.12996"),
        volatility_buffer_usd=Decimal("10"),
    )

    assert policy.minimum_reserve_usd == Decimal("1000.1300")
    assert policy.volatility_buffer_usd == Decimal("10.0000")


def test_burn_window_requires_ordered_timestamps():
    with pytest.raises(ValueError):
        BurnAnalysisWindow(
            window_start=datetime(2026, 1, 2, tzinfo=UTC),
            window_end=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_posture_selection_normalizes_as_of_utc_timestamp():
    selection = PostureInputSelection(
        liquidity_account_ids=["a-1"],
        burn_analysis_window=BurnAnalysisWindow(
            window_start=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
            window_end=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
        ),
        reserve_policy=ReservePolicyParameters(
            minimum_reserve_usd=Decimal("2500.00"),
            volatility_buffer_usd=Decimal("50.05"),
        ),
        as_of=datetime(2026, 1, 31, 7, 30, 0, 987654, tzinfo=UTC),
        currency="USD",
    )

    assert selection.as_of.isoformat() == "2026-01-31T07:30:00.987654+00:00"


def test_posture_selection_requires_unique_liquidity_accounts():
    with pytest.raises(ValueError):
        PostureInputSelection(
            liquidity_account_ids=["a-1", "a-1"],
            burn_analysis_window=BurnAnalysisWindow(
                window_start=datetime(2026, 1, 1, tzinfo=UTC),
                window_end=datetime(2026, 1, 31, tzinfo=UTC),
            ),
            reserve_policy=ReservePolicyParameters(
                minimum_reserve_usd=Decimal("1000"),
                volatility_buffer_usd=Decimal("25"),
            ),
            as_of=datetime(2026, 1, 31, tzinfo=UTC),
            currency="USD",
        )
