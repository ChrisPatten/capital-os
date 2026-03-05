from __future__ import annotations

import pytest

from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account, find_duplicate_risk_matches
from capital_os.domain.ledger.service import record_transaction_bundle


def _seed_accounts() -> tuple[str, str, str, str]:
    with transaction() as conn:
        cash = create_account(conn, {"code": "1000", "name": "Cash", "account_type": "asset"})
        revenue = create_account(conn, {"code": "4000", "name": "Revenue", "account_type": "income"})
        clearing = create_account(conn, {"code": "2000", "name": "Clearing", "account_type": "liability"})
        equity = create_account(conn, {"code": "9000", "name": "Equity", "account_type": "equity"})
    return cash, revenue, clearing, equity


def test_find_duplicate_risk_matches_exact_date_account_normalized_amount_deterministic(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    cash, revenue, clearing, equity = _seed_accounts()

    tx_1 = record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "dup-seed-1",
            "date": "2026-02-14T09:00:00Z",
            "description": "seed 1",
            "postings": [
                {"account_id": cash, "amount": "10.0000", "currency": "USD"},
                {"account_id": revenue, "amount": "-10.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-dup-seed-1",
        }
    )
    tx_2 = record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "dup-seed-2",
            "date": "2026-02-14T11:00:00Z",
            "description": "seed 2",
                "postings": [
                    {"account_id": clearing, "amount": "10.0000", "currency": "USD"},
                    {"account_id": equity, "amount": "-10.0000", "currency": "USD"},
                ],
                "correlation_id": "corr-dup-seed-2",
            }
    )

    with transaction() as conn:
        no_match = find_duplicate_risk_matches(
            conn,
            effective_date="2026-02-14T12:30:00Z",
            postings=[
                {"account_id": cash, "amount": "10.00004", "currency": "USD"},
                {"account_id": clearing, "amount": "10.0000", "currency": "USD"},
            ],
        )
        matches_tx_1 = find_duplicate_risk_matches(
            conn,
            effective_date="2026-02-14T12:30:00Z",
            postings=[
                {"account_id": cash, "amount": "10.00004", "currency": "USD"},
                {"account_id": revenue, "amount": "-10.0000", "currency": "USD"},
            ],
        )
        matches_tx_2 = find_duplicate_risk_matches(
            conn,
            effective_date="2026-02-14T12:30:00Z",
            postings=[
                {"account_id": clearing, "amount": "10.0000", "currency": "USD"},
                {"account_id": equity, "amount": "-10.0000", "currency": "USD"},
            ],
        )

    assert no_match == []
    assert [row["transaction_id"] for row in matches_tx_1] == [tx_1["transaction_id"]]
    assert [row["transaction_id"] for row in matches_tx_2] == [tx_2["transaction_id"]]
    assert [row["external_id"] for row in matches_tx_1] == ["dup-seed-1"]
    assert [row["external_id"] for row in matches_tx_2] == ["dup-seed-2"]
    assert all(row["match_reason"] == "same_account_date_amount" for row in matches_tx_1 + matches_tx_2)


def test_find_duplicate_risk_matches_requires_all_input_keys(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    cash, revenue, clearing, equity = _seed_accounts()

    record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "dup-partial-seed",
            "date": "2026-02-15T09:00:00Z",
            "description": "partial match seed",
            "postings": [
                {"account_id": cash, "amount": "10.0000", "currency": "USD"},
                {"account_id": revenue, "amount": "-10.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-dup-partial-seed",
        }
    )

    with transaction() as conn:
        matches = find_duplicate_risk_matches(
            conn,
            effective_date="2026-02-15T12:30:00Z",
            postings=[
                {"account_id": cash, "amount": "10.0000", "currency": "USD"},
                {"account_id": clearing, "amount": "10.0000", "currency": "USD"},
                {"account_id": equity, "amount": "-20.0000", "currency": "USD"},
            ],
        )

    assert matches == []
