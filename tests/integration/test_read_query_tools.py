import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import app
from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.domain.ledger.service import record_balance_snapshot, record_transaction_bundle


def _seed_accounts() -> dict[str, str]:
    with transaction() as conn:
        assets = create_account(conn, {"code": "1000", "name": "Assets", "account_type": "asset"})
        cash = create_account(
            conn,
            {
                "code": "1100",
                "name": "Cash",
                "account_type": "asset",
                "parent_account_id": assets,
            },
        )
        brokerage = create_account(
            conn,
            {
                "code": "1200",
                "name": "Brokerage",
                "account_type": "asset",
                "parent_account_id": assets,
            },
        )
        equity = create_account(conn, {"code": "3000", "name": "Equity", "account_type": "equity"})
    return {"assets": assets, "cash": cash, "brokerage": brokerage, "equity": equity}


def test_list_accounts_deterministic_stable_pagination(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app)
    ids = _seed_accounts()

    page_1 = client.post(
        "/tools/list_accounts",
        json={"limit": 2, "correlation_id": "corr-list-1"},
    )
    assert page_1.status_code == 200
    body_1 = page_1.json()
    assert [item["code"] for item in body_1["accounts"]] == ["1000", "1100"]
    assert body_1["next_cursor"]

    page_2 = client.post(
        "/tools/list_accounts",
        json={
            "limit": 2,
            "cursor": body_1["next_cursor"],
            "correlation_id": "corr-list-2",
        },
    )
    assert page_2.status_code == 200
    body_2 = page_2.json()
    assert [item["code"] for item in body_2["accounts"]] == ["1200", "3000"]
    assert body_2["next_cursor"] is None

    repeat = client.post(
        "/tools/list_accounts",
        json={"limit": 2, "correlation_id": "corr-list-3"},
    )
    assert repeat.status_code == 200
    assert repeat.json()["accounts"] == body_1["accounts"]

    with transaction() as conn:
        first_id = conn.execute("SELECT account_id FROM accounts WHERE code='1100'").fetchone()["account_id"]
    assert first_id == ids["cash"]


def test_get_account_tree_returns_deterministic_hierarchy(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app)
    ids = _seed_accounts()

    response = client.post(
        "/tools/get_account_tree",
        json={"root_account_id": ids["assets"], "correlation_id": "corr-tree-1"},
    )
    assert response.status_code == 200
    tree = response.json()["accounts"]
    assert len(tree) == 1
    assert tree[0]["code"] == "1000"
    assert [child["code"] for child in tree[0]["children"]] == ["1100", "1200"]

    repeat = client.post(
        "/tools/get_account_tree",
        json={"root_account_id": ids["assets"], "correlation_id": "corr-tree-2"},
    )
    assert repeat.status_code == 200
    assert repeat.json()["accounts"] == response.json()["accounts"]


def test_get_account_balances_source_policy_deterministic(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app)
    ids = _seed_accounts()

    record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "bal-1",
            "date": "2026-01-05T00:00:00Z",
            "description": "opening",
            "postings": [
                {"account_id": ids["cash"], "amount": "100.0000", "currency": "USD"},
                {"account_id": ids["equity"], "amount": "-100.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-bal-ledger",
        }
    )
    record_balance_snapshot(
        {
            "source_system": "pytest",
            "account_id": ids["cash"],
            "snapshot_date": "2026-01-06",
            "balance": "95.0000",
            "currency": "USD",
            "correlation_id": "corr-bal-snapshot",
        }
    )

    ledger_only = client.post(
        "/tools/get_account_balances",
        json={
            "as_of_date": "2026-01-10",
            "source_policy": "ledger_only",
            "correlation_id": "corr-bal-1",
        },
    )
    assert ledger_only.status_code == 200
    ledger_row = [row for row in ledger_only.json()["balances"] if row["account_id"] == ids["cash"]][0]
    assert ledger_row["balance"] == 100.0
    assert ledger_row["source_used"] == "ledger"

    snapshot_only = client.post(
        "/tools/get_account_balances",
        json={
            "as_of_date": "2026-01-10",
            "source_policy": "snapshot_only",
            "correlation_id": "corr-bal-2",
        },
    )
    assert snapshot_only.status_code == 200
    snapshot_row = [row for row in snapshot_only.json()["balances"] if row["account_id"] == ids["cash"]][0]
    assert snapshot_row["balance"] == 95.0
    assert snapshot_row["source_used"] == "snapshot"

    best_available = client.post(
        "/tools/get_account_balances",
        json={
            "as_of_date": "2026-01-10",
            "source_policy": "best_available",
            "correlation_id": "corr-bal-3",
        },
    )
    assert best_available.status_code == 200
    best_row = [row for row in best_available.json()["balances"] if row["account_id"] == ids["cash"]][0]
    assert best_row["balance"] == 95.0
    assert best_row["source_used"] == "snapshot"


def test_read_tools_do_not_mutate_canonical_tables(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app)
    ids = _seed_accounts()
    record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "bal-2",
            "date": "2026-01-05T00:00:00Z",
            "description": "opening",
            "postings": [
                {"account_id": ids["cash"], "amount": "100.0000", "currency": "USD"},
                {"account_id": ids["equity"], "amount": "-100.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-bal-ledger-2",
        }
    )
    record_balance_snapshot(
        {
            "source_system": "pytest",
            "account_id": ids["cash"],
            "snapshot_date": "2026-01-06",
            "balance": "95.0000",
            "currency": "USD",
            "correlation_id": "corr-bal-snapshot-2",
        }
    )

    with transaction() as conn:
        before = {
            "accounts": conn.execute("SELECT COUNT(*) AS c FROM accounts").fetchone()["c"],
            "transactions": conn.execute("SELECT COUNT(*) AS c FROM ledger_transactions").fetchone()["c"],
            "postings": conn.execute("SELECT COUNT(*) AS c FROM ledger_postings").fetchone()["c"],
            "snapshots": conn.execute("SELECT COUNT(*) AS c FROM balance_snapshots").fetchone()["c"],
            "obligations": conn.execute("SELECT COUNT(*) AS c FROM obligations").fetchone()["c"],
            "event_log": conn.execute("SELECT COUNT(*) AS c FROM event_log").fetchone()["c"],
        }

    assert (
        client.post("/tools/list_accounts", json={"correlation_id": "corr-read-nowrite-1"}).status_code
        == 200
    )
    assert (
        client.post(
            "/tools/get_account_tree",
            json={"root_account_id": ids["assets"], "correlation_id": "corr-read-nowrite-2"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/tools/get_account_balances",
            json={
                "as_of_date": "2026-01-10",
                "source_policy": "best_available",
                "correlation_id": "corr-read-nowrite-3",
            },
        ).status_code
        == 200
    )

    with transaction() as conn:
        after = {
            "accounts": conn.execute("SELECT COUNT(*) AS c FROM accounts").fetchone()["c"],
            "transactions": conn.execute("SELECT COUNT(*) AS c FROM ledger_transactions").fetchone()["c"],
            "postings": conn.execute("SELECT COUNT(*) AS c FROM ledger_postings").fetchone()["c"],
            "snapshots": conn.execute("SELECT COUNT(*) AS c FROM balance_snapshots").fetchone()["c"],
            "obligations": conn.execute("SELECT COUNT(*) AS c FROM obligations").fetchone()["c"],
            "event_log": conn.execute("SELECT COUNT(*) AS c FROM event_log").fetchone()["c"],
        }

    assert before["accounts"] == after["accounts"]
    assert before["transactions"] == after["transactions"]
    assert before["postings"] == after["postings"]
    assert before["snapshots"] == after["snapshots"]
    assert before["obligations"] == after["obligations"]
    assert after["event_log"] == before["event_log"] + 3
