import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import app
from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account


def test_success_and_validation_failures_logged(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app)
    with transaction() as conn:
        a1 = create_account(conn, {"code": "1000", "name": "Cash", "account_type": "asset"})
        a2 = create_account(conn, {"code": "3000", "name": "Equity", "account_type": "equity"})

    ok_payload = {
        "source_system": "pytest",
        "external_id": "evt-1",
        "date": "2026-01-01T00:00:00Z",
        "description": "seed",
        "postings": [
            {"account_id": a1, "amount": "1.00", "currency": "USD"},
            {"account_id": a2, "amount": "-1.00", "currency": "USD"},
        ],
        "correlation_id": "corr-evt-1",
    }
    bad_payload = {"source_system": "pytest", "correlation_id": "corr-evt-2"}

    assert client.post("/tools/record_transaction_bundle", json=ok_payload).status_code == 200
    assert client.post("/tools/record_transaction_bundle", json=bad_payload).status_code == 422

    with transaction() as conn:
        rows = conn.execute("SELECT tool_name, status FROM event_log ORDER BY created_at").fetchall()
    assert len(rows) == 2
    assert rows[0]["status"] == "ok"
    assert rows[1]["status"] == "validation_error"
