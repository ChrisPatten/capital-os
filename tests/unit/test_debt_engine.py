from __future__ import annotations

from capital_os.domain.debt.engine import DebtAnalysisInputs, analyze_liabilities_with_hash


def test_analyze_liabilities_stable_order_for_same_input():
    payload = DebtAnalysisInputs(
        liabilities=[
            {"liability_id": "loan-a", "current_balance": "10000.0000", "apr": "6.5000", "minimum_payment": "225.0000"},
            {"liability_id": "loan-b", "current_balance": "4000.0000", "apr": "19.9000", "minimum_payment": "150.0000"},
            {"liability_id": "loan-c", "current_balance": "2500.0000", "apr": "19.9000", "minimum_payment": "150.0000"},
        ],
        optional_payoff_amount="1000.0000",
    )

    first = analyze_liabilities_with_hash(payload)
    second = analyze_liabilities_with_hash(payload)

    assert first == second
    assert first["output_hash"] == second["output_hash"]
    assert [row["liability_id"] for row in first["ranked_liabilities"]] == ["loan-b", "loan-a", "loan-c"]


def test_analyze_liabilities_tie_breaker_uses_liability_id():
    payload = DebtAnalysisInputs(
        liabilities=[
            {"liability_id": "z-loan", "current_balance": "5000.0000", "apr": "10.0000", "minimum_payment": "120.0000"},
            {"liability_id": "a-loan", "current_balance": "5000.0000", "apr": "10.0000", "minimum_payment": "120.0000"},
        ]
    )

    result = analyze_liabilities_with_hash(payload)
    assert [row["liability_id"] for row in result["ranked_liabilities"]] == ["a-loan", "z-loan"]


def test_analyze_liabilities_applies_optional_payoff_sensitivity():
    payload = DebtAnalysisInputs(
        liabilities=[
            {"liability_id": "loan-a", "current_balance": "1000.0000", "apr": "20.0000", "minimum_payment": "60.0000"},
            {"liability_id": "loan-b", "current_balance": "3000.0000", "apr": "12.0000", "minimum_payment": "80.0000"},
        ],
        optional_payoff_amount="1200.0000",
    )

    result = analyze_liabilities_with_hash(payload)
    ranked = result["ranked_liabilities"]

    assert ranked[0]["liability_id"] == "loan-b"
    assert ranked[0]["payoff_applied"] == "1200.0000"
    assert ranked[0]["post_payoff_balance"] == "1800.0000"
    assert ranked[0]["cashflow_freed"] == "0.0000"
    assert ranked[1]["payoff_applied"] == "0.0000"
    assert ranked[1]["post_payoff_balance"] == "1000.0000"
    assert result["total_cashflow_freed"] == "0.0000"
    assert result["total_reserve_impact"] == "-1200.0000"
