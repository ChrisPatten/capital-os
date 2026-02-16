import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import app
from tests.support.auth import AUTH_HEADERS
from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.domain.ledger.service import record_balance_snapshot, record_transaction_bundle


def _seed_reconciliation_state() -> dict[str, str]:
    with transaction() as conn:
        cash = create_account(conn, {"code": "1100", "name": "Cash", "account_type": "asset"})
        equity = create_account(conn, {"code": "3000", "name": "Equity", "account_type": "equity"})

    record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "reconcile-tx-1",
            "date": "2026-01-05T00:00:00Z",
            "description": "seed reconciliation",
            "postings": [
                {"account_id": cash, "amount": "100.0000", "currency": "USD"},
                {"account_id": equity, "amount": "-100.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-reconcile-seed-ledger",
        }
    )
    record_balance_snapshot(
        {
            "source_system": "pytest",
            "account_id": cash,
            "snapshot_date": "2026-01-06",
            "balance": "95.0000",
            "currency": "USD",
            "correlation_id": "corr-reconcile-seed-snapshot",
        }
    )
    return {"cash": cash}


def test_reconcile_account_returns_deterministic_delta_and_proposed_adjustment(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    ids = _seed_reconciliation_state()
    client = TestClient(app, headers=AUTH_HEADERS)

    with transaction() as conn:
        before_tx_count = conn.execute("SELECT COUNT(*) AS c FROM ledger_transactions").fetchone()["c"]

    response = client.post(
        "/tools/reconcile_account",
        json={
            "account_id": ids["cash"],
            "as_of_date": "2026-01-10",
            "method": "snapshot_only",
            "correlation_id": "corr-reconcile-1",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["ledger_balance"] == 100.0
    assert body["snapshot_balance"] == 95.0
    assert body["delta"] == -5.0
    assert body["source_used"] == "snapshot"
    assert body["suggested_adjustment_bundle"]["status"] == "proposed"
    assert body["suggested_adjustment_bundle"]["auto_commit"] is False
    postings = body["suggested_adjustment_bundle"]["postings"]
    assert len(postings) == 2
    assert postings[0]["account_id"] == ids["cash"]
    assert postings[0]["amount"] == -5.0
    assert postings[1]["account_id"] == "__OFFSET_ACCOUNT_REQUIRED__"
    assert postings[1]["amount"] == 5.0

    with transaction() as conn:
        after_tx_count = conn.execute("SELECT COUNT(*) AS c FROM ledger_transactions").fetchone()["c"]
    assert after_tx_count == before_tx_count


def test_reconcile_account_ledger_only_returns_no_adjustment(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    ids = _seed_reconciliation_state()
    client = TestClient(app, headers=AUTH_HEADERS)

    response = client.post(
        "/tools/reconcile_account",
        json={
            "account_id": ids["cash"],
            "as_of_date": "2026-01-10",
            "method": "ledger_only",
            "correlation_id": "corr-reconcile-2",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["source_used"] == "ledger"
    assert body["suggested_adjustment_bundle"] is None


def test_reconcile_account_not_found_is_deterministic(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    payload = {
        "account_id": "does-not-exist",
        "as_of_date": "2026-01-10",
        "method": "best_available",
        "correlation_id": "corr-reconcile-missing",
    }
    first = client.post("/tools/reconcile_account", json=payload)
    second = client.post("/tools/reconcile_account", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status"] == "account_not_found"
    assert first.json() == second.json()


def test_reconcile_account_best_available_without_snapshot_uses_ledger(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    with transaction() as conn:
        cash = create_account(conn, {"code": "1100", "name": "Cash", "account_type": "asset"})
        equity = create_account(conn, {"code": "3000", "name": "Equity", "account_type": "equity"})

    record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "reconcile-tx-ledger-only",
            "date": "2026-01-05T00:00:00Z",
            "description": "ledger only",
            "postings": [
                {"account_id": cash, "amount": "100.0000", "currency": "USD"},
                {"account_id": equity, "amount": "-100.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-reconcile-ledger-only",
        }
    )

    client = TestClient(app, headers=AUTH_HEADERS)
    response = client.post(
        "/tools/reconcile_account",
        json={
            "account_id": cash,
            "as_of_date": "2026-01-10",
            "method": "best_available",
            "correlation_id": "corr-reconcile-best-available",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["source_used"] == "ledger"
    assert body["snapshot_balance"] is None
    assert body["delta"] is None
    assert body["suggested_adjustment_bundle"] is None
