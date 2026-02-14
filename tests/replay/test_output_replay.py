import pytest

from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.domain.ledger.service import record_transaction_bundle
from capital_os.domain.posture.engine import (
    PostureComputationInputs,
    compute_posture_metrics_with_hash,
)


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


def test_posture_engine_output_hash_reproducible_for_same_input():
    payload = PostureComputationInputs(
        liquidity="18000.0000",
        fixed_burn="3500.0000",
        variable_burn="1200.0000",
        minimum_reserve="10000.0000",
        volatility_buffer="1500.0000",
    )

    first = compute_posture_metrics_with_hash(payload)
    second = compute_posture_metrics_with_hash(payload)

    assert first["output_hash"] == second["output_hash"]
    assert first == second
    assert list(first["explanation"].keys()) == ["contributing_balances", "reserve_assumptions"]
    assert first["explanation"]["contributing_balances"][0]["name"] == "liquidity"
