import pytest

from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.domain.ledger.service import record_balance_snapshot, record_transaction_bundle
from capital_os.tools.reconcile_account import handle as reconcile_account_tool


def _seed_reconciliation_state() -> str:
    with transaction() as conn:
        cash = create_account(conn, {"code": "1100", "name": "Cash", "account_type": "asset"})
        equity = create_account(conn, {"code": "3000", "name": "Equity", "account_type": "equity"})

    record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "reconcile-replay-tx-1",
            "date": "2026-01-05T00:00:00Z",
            "description": "seed reconciliation replay",
            "postings": [
                {"account_id": cash, "amount": "100.0000", "currency": "USD"},
                {"account_id": equity, "amount": "-100.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-reconcile-replay-ledger",
        }
    )
    record_balance_snapshot(
        {
            "source_system": "pytest",
            "account_id": cash,
            "snapshot_date": "2026-01-06",
            "balance": "95.0000",
            "currency": "USD",
            "correlation_id": "corr-reconcile-replay-snapshot",
        }
    )
    return cash


def test_reconcile_account_output_hash_reproducible_and_non_mutating(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    account_id = _seed_reconciliation_state()
    payload = {
        "account_id": account_id,
        "as_of_date": "2026-01-10",
        "method": "snapshot_only",
        "correlation_id": "corr-reconcile-replay",
    }

    with transaction() as conn:
        before_tx = conn.execute("SELECT COUNT(*) AS c FROM ledger_transactions").fetchone()["c"]

    first = reconcile_account_tool(payload).model_dump(mode="json")
    second = reconcile_account_tool(payload).model_dump(mode="json")
    assert first == second
    assert first["output_hash"] == second["output_hash"]
    assert first["suggested_adjustment_bundle"]["auto_commit"] is False

    with transaction() as conn:
        after_tx = conn.execute("SELECT COUNT(*) AS c FROM ledger_transactions").fetchone()["c"]
    assert after_tx == before_tx
