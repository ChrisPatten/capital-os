import random
from decimal import Decimal

import pytest

from capital_os.config import get_settings
from capital_os.db.session import transaction
from capital_os.domain.approval.service import approve_proposed_transaction, reject_proposed_transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.domain.ledger.service import record_transaction_bundle
from capital_os.tools.analyze_debt import handle as analyze_debt_tool
from capital_os.tools.compute_capital_posture import handle as compute_capital_posture_tool
from capital_os.tools.simulate_spend import handle as simulate_spend_tool


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_output_hash_reproducible_for_same_input(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    with transaction() as conn:
        a1 = create_account(conn, {"code": "1000", "name": "Cash", "account_type": "asset"})
        a2 = create_account(conn, {"code": "9100", "name": "Owner Equity", "account_type": "equity"})

    payload = {
        "source_system": "pytest",
        "external_id": "replay-1",
        "date": "2026-01-01T00:00:00Z",
        "description": "owner seed",
        "postings": [
            {"account_id": a1, "amount": "100.00", "currency": "USD"},
            {"account_id": a2, "amount": "-100.00", "currency": "USD"},
        ],
        "correlation_id": "corr-replay",
    }

    first = record_transaction_bundle(payload)
    second = record_transaction_bundle(payload)
    assert first["output_hash"] == second["output_hash"]


def test_seeded_repeat_runs_keep_posture_output_hash_stable(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    for seed in range(1, 21):
        rng = random.Random(seed)
        payload = {
            "liquidity": f"{Decimal(rng.randint(10_000, 100_000)):.4f}",
            "fixed_burn": f"{Decimal(rng.randint(2_000, 20_000)):.4f}",
            "variable_burn": f"{Decimal(rng.randint(500, 7_000)):.4f}",
            "minimum_reserve": f"{Decimal(rng.randint(5_000, 60_000)):.4f}",
            "volatility_buffer": f"{Decimal(rng.randint(0, 5_000)):.4f}",
            "correlation_id": f"corr-posture-seed-{seed}",
        }

        first = compute_capital_posture_tool(payload).model_dump(mode="json")
        second = compute_capital_posture_tool(payload).model_dump(mode="json")

        assert first["output_hash"] == second["output_hash"]
        assert first == second


def test_seeded_repeat_runs_keep_simulation_output_hash_stable(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    for seed in range(1, 21):
        rng = random.Random(seed)
        one_time_amount = Decimal(rng.randint(50, 800))
        recurring_amount = Decimal(rng.randint(20, 250))
        horizon = rng.randint(2, 6)
        occurrences = rng.randint(2, 6)

        payload = {
            "starting_liquidity": f"{Decimal(rng.randint(1_000, 20_000)):.4f}",
            "start_date": "2026-01-01",
            "horizon_periods": horizon,
            "spends": [
                {
                    "spend_id": f"one-time-{seed}",
                    "amount": f"{one_time_amount:.4f}",
                    "type": "one_time",
                    "spend_date": "2026-01-10",
                },
                {
                    "spend_id": f"recurring-{seed}",
                    "amount": f"{recurring_amount:.4f}",
                    "type": "recurring",
                    "start_date": "2026-01-05",
                    "cadence": "weekly",
                    "occurrences": occurrences,
                },
            ],
            "correlation_id": f"corr-sim-seed-{seed}",
        }

        first = simulate_spend_tool(payload).model_dump(mode="json")
        second = simulate_spend_tool(payload).model_dump(mode="json")

        assert first["output_hash"] == second["output_hash"]
        assert first == second


def test_seeded_repeat_runs_keep_debt_output_hash_stable(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    for seed in range(1, 21):
        rng = random.Random(seed)
        payload = {
            "liabilities": [
                {
                    "liability_id": f"loan-{seed}-a",
                    "current_balance": f"{Decimal(rng.randint(2_000, 12_000)):.4f}",
                    "apr": f"{Decimal(rng.randint(300, 2500)) / Decimal('100'):.4f}",
                    "minimum_payment": f"{Decimal(rng.randint(50, 400)):.4f}",
                },
                {
                    "liability_id": f"loan-{seed}-b",
                    "current_balance": f"{Decimal(rng.randint(1_500, 20_000)):.4f}",
                    "apr": f"{Decimal(rng.randint(100, 2200)) / Decimal('100'):.4f}",
                    "minimum_payment": f"{Decimal(rng.randint(40, 500)):.4f}",
                },
            ],
            "optional_payoff_amount": f"{Decimal(rng.randint(0, 4_000)):.4f}",
            "reserve_floor": f"{Decimal(rng.randint(0, 3_500)):.4f}",
            "correlation_id": f"corr-debt-seed-{seed}",
        }

        first = analyze_debt_tool(payload).model_dump(mode="json")
        second = analyze_debt_tool(payload).model_dump(mode="json")

        assert first["output_hash"] == second["output_hash"]
        assert first == second


def test_approval_tools_output_hash_reproducible_on_replay(db_available, monkeypatch):
    if not db_available:
        pytest.skip("database unavailable")

    monkeypatch.setenv("CAPITAL_OS_APPROVAL_THRESHOLD_AMOUNT", "100.0000")
    get_settings.cache_clear()

    with transaction() as conn:
        debit = create_account(conn, {"code": "1200", "name": "Replay Cash", "account_type": "asset"})
        credit = create_account(conn, {"code": "2200", "name": "Replay Debt", "account_type": "liability"})

    proposed = record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "approval-replay-1",
            "date": "2026-01-01T00:00:00Z",
            "description": "approval replay",
            "postings": [
                {"account_id": debit, "amount": "250.0000", "currency": "USD"},
                {"account_id": credit, "amount": "-250.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-approval-proposed",
        }
    )
    assert proposed["status"] == "proposed"

    first_approve = approve_proposed_transaction(
        {
            "proposal_id": proposed["proposal_id"],
            "reason": "approved",
            "correlation_id": "corr-approval-approve-1",
        }
    )
    second_approve = approve_proposed_transaction(
        {
            "proposal_id": proposed["proposal_id"],
            "reason": "approved replay",
            "correlation_id": "corr-approval-approve-2",
        }
    )

    assert first_approve["output_hash"] == second_approve["output_hash"]
    assert first_approve == second_approve

    proposed_reject = record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "approval-replay-2",
            "date": "2026-01-01T00:00:00Z",
            "description": "approval reject replay",
            "postings": [
                {"account_id": debit, "amount": "180.0000", "currency": "USD"},
                {"account_id": credit, "amount": "-180.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-approval-proposed-reject",
        }
    )
    assert proposed_reject["status"] == "proposed"

    first_reject = reject_proposed_transaction(
        {
            "proposal_id": proposed_reject["proposal_id"],
            "reason": "not aligned",
            "correlation_id": "corr-approval-reject-1",
        }
    )
    second_reject = reject_proposed_transaction(
        {
            "proposal_id": proposed_reject["proposal_id"],
            "reason": "ignored in replay",
            "correlation_id": "corr-approval-reject-2",
        }
    )

    assert first_reject["output_hash"] == second_reject["output_hash"]
    assert first_reject == second_reject
