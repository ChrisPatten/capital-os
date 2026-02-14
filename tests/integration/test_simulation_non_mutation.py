import pytest

from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.domain.ledger.service import record_transaction_bundle
from capital_os.domain.simulation.service import simulate_spend


def _table_counts() -> dict[str, int]:
    with transaction() as conn:
        return {
            "ledger_transactions": conn.execute("SELECT COUNT(*) AS c FROM ledger_transactions").fetchone()["c"],
            "ledger_postings": conn.execute("SELECT COUNT(*) AS c FROM ledger_postings").fetchone()["c"],
            "balance_snapshots": conn.execute("SELECT COUNT(*) AS c FROM balance_snapshots").fetchone()["c"],
            "obligations": conn.execute("SELECT COUNT(*) AS c FROM obligations").fetchone()["c"],
            "event_log": conn.execute("SELECT COUNT(*) AS c FROM event_log").fetchone()["c"],
        }


def test_simulation_is_read_only_and_deterministic(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    with transaction() as conn:
        cash = create_account(conn, {"code": "1000", "name": "Cash", "account_type": "asset"})
        equity = create_account(conn, {"code": "9100", "name": "Equity", "account_type": "equity"})

    record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "sim-seed-1",
            "date": "2026-01-01T00:00:00Z",
            "description": "seed",
            "postings": [
                {"account_id": cash, "amount": "5000.0000", "currency": "USD"},
                {"account_id": equity, "amount": "-5000.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-sim-seed-1",
        }
    )

    payload = {
        "starting_liquidity": "5000.0000",
        "start_date": "2026-01-01",
        "horizon_periods": 3,
        "spends": [
            {
                "spend_id": "ot-1",
                "amount": "250.0000",
                "type": "one_time",
                "spend_date": "2026-02-14",
            },
            {
                "spend_id": "rc-1",
                "amount": "100.0000",
                "type": "recurring",
                "start_date": "2026-01-10",
                "cadence": "monthly",
                "occurrences": 2,
            },
        ],
    }

    before = _table_counts()
    first = simulate_spend(payload)
    second = simulate_spend(payload)
    after = _table_counts()

    assert first == second
    assert first["output_hash"] == second["output_hash"]
    assert before == after
