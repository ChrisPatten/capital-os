import pytest

from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.domain.ledger.service import record_transaction_bundle


def _seed_accounts():
    with transaction() as conn:
        a1 = create_account(conn, {"code": "1000", "name": "Cash", "account_type": "asset"})
        a2 = create_account(conn, {"code": "4000", "name": "Income", "account_type": "income"})
    return a1, a2


def test_balanced_transaction_commits(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    a1, a2 = _seed_accounts()
    result = record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "tx-1",
            "date": "2026-01-01T00:00:00Z",
            "description": "deposit",
            "postings": [
                {"account_id": a1, "amount": "10.00", "currency": "USD"},
                {"account_id": a2, "amount": "-10.00", "currency": "USD"},
            ],
            "correlation_id": "corr-1",
        }
    )
    assert result["status"] == "committed"
    assert len(result["posting_ids"]) == 2


def test_unbalanced_transaction_rejected(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    a1, a2 = _seed_accounts()
    with pytest.raises(Exception):
        record_transaction_bundle(
            {
                "source_system": "pytest",
                "external_id": "tx-2",
                "date": "2026-01-01T00:00:00Z",
                "description": "bad",
                "postings": [
                    {"account_id": a1, "amount": "10.00", "currency": "USD"},
                    {"account_id": a2, "amount": "-9.99", "currency": "USD"},
                ],
                "correlation_id": "corr-2",
            }
        )
