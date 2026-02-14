import pytest

from capital_os.domain.simulation.engine import (
    SimulationInputs,
    compute_simulation_projection,
    compute_simulation_projection_with_hash,
)


def test_one_time_spend_branch_projects_expected_period_total():
    inputs = SimulationInputs.model_validate(
        {
            "starting_liquidity": "1000.0000",
            "start_date": "2026-01-01",
            "horizon_periods": 3,
            "spends": [
                {
                    "spend_id": "ot-1",
                    "amount": "250.0000",
                    "type": "one_time",
                    "spend_date": "2026-02-10",
                }
            ],
        }
    )

    projection = compute_simulation_projection(inputs)

    assert [f"{p.total_spend:.4f}" for p in projection.periods] == ["0.0000", "250.0000", "0.0000"]
    assert [f"{p.ending_liquidity:.4f}" for p in projection.periods] == [
        "1000.0000",
        "750.0000",
        "750.0000",
    ]


def test_recurring_spend_branch_projects_monthly_occurrences():
    inputs = SimulationInputs.model_validate(
        {
            "starting_liquidity": "1000.0000",
            "start_date": "2026-01-01",
            "horizon_periods": 4,
            "spends": [
                {
                    "spend_id": "rc-1",
                    "amount": "100.0000",
                    "type": "recurring",
                    "start_date": "2026-01-15",
                    "cadence": "monthly",
                    "occurrences": 3,
                }
            ],
        }
    )

    projection = compute_simulation_projection(inputs)

    assert [f"{p.recurring_total:.4f}" for p in projection.periods] == ["100.0000", "100.0000", "100.0000", "0.0000"]
    assert [f"{p.ending_liquidity:.4f}" for p in projection.periods] == [
        "900.0000",
        "800.0000",
        "700.0000",
        "700.0000",
    ]


def test_projection_output_hash_is_deterministic_for_same_input():
    inputs = SimulationInputs.model_validate(
        {
            "starting_liquidity": "5000.0000",
            "start_date": "2026-01-01",
            "horizon_periods": 2,
            "spends": [
                {
                    "spend_id": "rc-1",
                    "amount": "50.0000",
                    "type": "recurring",
                    "start_date": "2026-01-05",
                    "cadence": "weekly",
                    "occurrences": 6,
                },
                {
                    "spend_id": "ot-1",
                    "amount": "125.0000",
                    "type": "one_time",
                    "spend_date": "2026-01-20",
                },
            ],
        }
    )

    first = compute_simulation_projection_with_hash(inputs)
    second = compute_simulation_projection_with_hash(inputs)

    assert first == second
    assert first["output_hash"] == second["output_hash"]


def test_duplicate_spend_ids_are_rejected():
    with pytest.raises(ValueError, match="spend_id values must be unique"):
        SimulationInputs.model_validate(
            {
                "starting_liquidity": "1000.0000",
                "start_date": "2026-01-01",
                "horizon_periods": 1,
                "spends": [
                    {"spend_id": "dup", "amount": "1.0000", "type": "one_time", "spend_date": "2026-01-01"},
                    {"spend_id": "dup", "amount": "2.0000", "type": "one_time", "spend_date": "2026-01-02"},
                ],
            }
        )
