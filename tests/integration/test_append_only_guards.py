import pytest

from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.domain.ledger.service import record_transaction_bundle


def test_append_only_blocks_update_on_transaction_table(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    with transaction() as conn:
        a1 = create_account(conn, {"code": "1000", "name": "Cash", "account_type": "asset"})
        a2 = create_account(conn, {"code": "9000", "name": "Opening", "account_type": "equity"})
    result = record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "app-1",
            "date": "2026-01-01T00:00:00Z",
            "description": "opening",
            "postings": [
                {"account_id": a1, "amount": "2.00", "currency": "USD"},
                {"account_id": a2, "amount": "-2.00", "currency": "USD"},
            ],
            "correlation_id": "corr-app-1",
        }
    )

    with pytest.raises(Exception):
        with transaction() as conn:
            conn.execute(
                "UPDATE ledger_transactions SET description=? WHERE transaction_id=?",
                ("x", result["transaction_id"]),
            )
