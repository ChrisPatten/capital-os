from __future__ import annotations

from decimal import Decimal

import pytest

from capital_os.domain.posture.engine import (
    PostureComputationInputs,
    compute_posture_metrics,
    compute_posture_metrics_with_hash,
)


def test_posture_engine_computes_all_fr06_metrics():
    inputs = PostureComputationInputs(
        liquidity=Decimal("18000"),
        fixed_burn=Decimal("3500"),
        variable_burn=Decimal("1200"),
        minimum_reserve=Decimal("10000"),
        volatility_buffer=Decimal("1500"),
    )

    metrics = compute_posture_metrics(inputs)

    assert metrics.fixed_burn == Decimal("3500.0000")
    assert metrics.variable_burn == Decimal("1200.0000")
    assert metrics.volatility_buffer == Decimal("1500.0000")
    assert metrics.reserve_target == Decimal("11500.0000")
    assert metrics.liquidity == Decimal("18000.0000")
    assert metrics.liquidity_surplus == Decimal("6500.0000")
    assert metrics.reserve_ratio == Decimal("1.5652")
    assert metrics.risk_band == "stable"


def test_posture_engine_round_half_even_normalization():
    inputs = PostureComputationInputs(
        liquidity=Decimal("100.00005"),
        fixed_burn=Decimal("10.00005"),
        variable_burn=Decimal("5.00005"),
        minimum_reserve=Decimal("80.00005"),
        volatility_buffer=Decimal("20.00005"),
    )

    metrics = compute_posture_metrics(inputs)

    assert metrics.liquidity == Decimal("100.0000")
    assert metrics.fixed_burn == Decimal("10.0000")
    assert metrics.variable_burn == Decimal("5.0000")
    assert metrics.reserve_target == Decimal("100.0000")
    assert metrics.reserve_ratio == Decimal("1.0000")


def test_posture_engine_handles_zero_reserve_target_without_division_error():
    inputs = PostureComputationInputs(
        liquidity=Decimal("500.0000"),
        fixed_burn=Decimal("100.0000"),
        variable_burn=Decimal("50.0000"),
        minimum_reserve=Decimal("0"),
        volatility_buffer=Decimal("0"),
    )

    metrics = compute_posture_metrics(inputs)

    assert metrics.reserve_target == Decimal("0.0000")
    assert metrics.reserve_ratio == Decimal("0.0000")
    assert metrics.risk_band == "critical"


@pytest.mark.parametrize(
    ("minimum_reserve", "expected_target", "expected_ratio"),
    [
        (Decimal("0.00004"), Decimal("0.0000"), Decimal("0.0000")),
        (Decimal("0.00006"), Decimal("0.0001"), Decimal("5000000.0000")),
    ],
)
def test_posture_engine_near_zero_reserve_target_is_deterministic(
    minimum_reserve: Decimal, expected_target: Decimal, expected_ratio: Decimal
):
    inputs = PostureComputationInputs(
        liquidity=Decimal("500.0000"),
        fixed_burn=Decimal("100.0000"),
        variable_burn=Decimal("50.0000"),
        minimum_reserve=minimum_reserve,
        volatility_buffer=Decimal("0"),
    )

    metrics = compute_posture_metrics(inputs)

    assert metrics.reserve_target == expected_target
    assert metrics.reserve_ratio == expected_ratio


@pytest.mark.parametrize(
    ("ratio", "expected_band"),
    [
        (Decimal("0.2499"), "critical"),
        (Decimal("0.5000"), "elevated"),
        (Decimal("0.7500"), "elevated"),
        (Decimal("1.0000"), "guarded"),
        (Decimal("1.2500"), "guarded"),
        (Decimal("1.5000"), "stable"),
    ],
)
def test_posture_engine_risk_band_is_deterministic(ratio: Decimal, expected_band: str):
    reserve_target = Decimal("100.0000")
    inputs = PostureComputationInputs(
        liquidity=reserve_target * ratio,
        fixed_burn=Decimal("10.0000"),
        variable_burn=Decimal("5.0000"),
        minimum_reserve=Decimal("90.0000"),
        volatility_buffer=Decimal("10.0000"),
    )

    metrics = compute_posture_metrics(inputs)
    assert metrics.risk_band == expected_band


def test_posture_engine_hash_output_is_stable_for_same_input():
    inputs = PostureComputationInputs(
        liquidity=Decimal("18000"),
        fixed_burn=Decimal("3500"),
        variable_burn=Decimal("1200"),
        minimum_reserve=Decimal("10000"),
        volatility_buffer=Decimal("1500"),
    )

    first = compute_posture_metrics_with_hash(inputs)
    second = compute_posture_metrics_with_hash(inputs)

    assert first["output_hash"] == second["output_hash"]
    assert first == second


def test_posture_engine_hash_output_is_serialized_deterministically():
    inputs = PostureComputationInputs(
        liquidity=Decimal("18000"),
        fixed_burn=Decimal("3500"),
        variable_burn=Decimal("1200"),
        minimum_reserve=Decimal("10000"),
        volatility_buffer=Decimal("1500"),
    )

    output = compute_posture_metrics_with_hash(inputs)

    assert list(output.keys()) == [
        "fixed_burn",
        "variable_burn",
        "volatility_buffer",
        "reserve_target",
        "liquidity",
        "liquidity_surplus",
        "reserve_ratio",
        "risk_band",
        "explanation",
        "output_hash",
    ]
    assert output["fixed_burn"] == "3500.0000"
    assert output["reserve_ratio"] == "1.5652"
    assert list(output["explanation"].keys()) == ["contributing_balances", "reserve_assumptions"]
    assert [item["name"] for item in output["explanation"]["contributing_balances"]] == [
        "liquidity",
        "fixed_burn",
        "variable_burn",
    ]
    assert list(output["explanation"]["reserve_assumptions"].keys()) == [
        "minimum_reserve",
        "volatility_buffer",
        "reserve_target",
    ]


def test_posture_engine_explanation_payload_has_no_secret_fields():
    inputs = PostureComputationInputs(
        liquidity=Decimal("18000"),
        fixed_burn=Decimal("3500"),
        variable_burn=Decimal("1200"),
        minimum_reserve=Decimal("10000"),
        volatility_buffer=Decimal("1500"),
    )

    output = compute_posture_metrics_with_hash(inputs)
    serialized = str(output["explanation"]).lower()
    assert "secret" not in serialized
    assert "token" not in serialized
    assert "password" not in serialized


def test_posture_engine_rejects_negative_burn_and_reserve_inputs():
    with pytest.raises(ValueError, match="non-negative"):
        PostureComputationInputs(
            liquidity=Decimal("100.0000"),
            fixed_burn=Decimal("-1.0000"),
            variable_burn=Decimal("10.0000"),
            minimum_reserve=Decimal("50.0000"),
            volatility_buffer=Decimal("0.0000"),
        )

    with pytest.raises(ValueError, match="non-negative"):
        PostureComputationInputs(
            liquidity=Decimal("100.0000"),
            fixed_burn=Decimal("1.0000"),
            variable_burn=Decimal("10.0000"),
            minimum_reserve=Decimal("-50.0000"),
            volatility_buffer=Decimal("0.0000"),
        )
