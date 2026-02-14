import pytest

from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.domain.ledger.service import record_transaction_bundle


def test_duplicate_external_id_replays_canonical_result(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    with transaction() as conn:
        a1 = create_account(conn, {"code": "1000", "name": "Cash", "account_type": "asset"})
        a2 = create_account(conn, {"code": "2000", "name": "Liability", "account_type": "liability"})

    payload = {
        "source_system": "pytest",
        "external_id": "dup-1",
        "date": "2026-01-01T00:00:00Z",
        "description": "loan",
        "postings": [
            {"account_id": a1, "amount": "25.00", "currency": "USD"},
            {"account_id": a2, "amount": "-25.00", "currency": "USD"},
        ],
        "correlation_id": "corr-dup",
    }
    first = record_transaction_bundle(payload)
    second = record_transaction_bundle(payload)

    assert first["transaction_id"] == second["transaction_id"]
    assert second["status"] == "idempotent-replay"
