import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import app
from tests.support.auth import AUTH_HEADERS
from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.domain.ledger.service import create_or_update_obligation, record_transaction_bundle


def _seed_accounts() -> dict[str, str]:
    with transaction() as conn:
        cash = create_account(conn, {"code": "1100", "name": "Cash", "account_type": "asset"})
        equity = create_account(conn, {"code": "3100", "name": "Equity", "account_type": "equity"})
        payable = create_account(conn, {"code": "2100", "name": "Payable", "account_type": "liability"})
    return {"cash": cash, "equity": equity, "payable": payable}


def _seed_transactions(ids: dict[str, str]) -> None:
    record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "tx-q-1",
            "date": "2026-01-01T00:00:00Z",
            "description": "tx 1",
            "postings": [
                {"account_id": ids["cash"], "amount": "100.0000", "currency": "USD"},
                {"account_id": ids["equity"], "amount": "-100.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-qtx-1",
        }
    )
    record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "tx-q-2",
            "date": "2026-01-02T00:00:00Z",
            "description": "tx 2",
            "postings": [
                {"account_id": ids["cash"], "amount": "50.0000", "currency": "USD"},
                {"account_id": ids["payable"], "amount": "-50.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-qtx-2",
        }
    )
    record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "tx-q-3",
            "date": "2026-01-03T00:00:00Z",
            "description": "tx 3",
            "postings": [
                {"account_id": ids["cash"], "amount": "25.0000", "currency": "USD"},
                {"account_id": ids["equity"], "amount": "-25.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-qtx-3",
        }
    )


def _seed_obligations(ids: dict[str, str]) -> None:
    create_or_update_obligation(
        {
            "source_system": "pytest",
            "name": "Rent",
            "account_id": ids["payable"],
            "cadence": "monthly",
            "expected_amount": "2000.0000",
            "variability_flag": False,
            "next_due_date": "2026-02-01",
            "metadata": {"kind": "fixed"},
            "correlation_id": "corr-ob-1",
        }
    )
    create_or_update_obligation(
        {
            "source_system": "pytest",
            "name": "Utilities",
            "account_id": ids["payable"],
            "cadence": "monthly",
            "expected_amount": "250.0000",
            "variability_flag": True,
            "next_due_date": "2026-02-10",
            "metadata": {"kind": "variable"},
            "correlation_id": "corr-ob-2",
        }
    )


def test_transaction_query_tools_are_deterministic(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    ids = _seed_accounts()
    _seed_transactions(ids)

    client = TestClient(app, headers=AUTH_HEADERS)
    first = client.post(
        "/tools/list_transactions",
        json={"limit": 2, "correlation_id": "corr-list-tx-1"},
    )
    assert first.status_code == 200
    body = first.json()
    assert [t["external_id"] for t in body["transactions"]] == ["tx-q-3", "tx-q-2"]
    assert body["next_cursor"]

    second = client.post(
        "/tools/list_transactions",
        json={"limit": 2, "cursor": body["next_cursor"], "correlation_id": "corr-list-tx-2"},
    )
    assert second.status_code == 200
    assert [t["external_id"] for t in second.json()["transactions"]] == ["tx-q-1"]

    lookup = client.post(
        "/tools/get_transaction_by_external_id",
        json={"source_system": "pytest", "external_id": "tx-q-2", "correlation_id": "corr-get-tx"},
    )
    assert lookup.status_code == 200
    transaction = lookup.json()["transaction"]
    assert transaction["external_id"] == "tx-q-2"
    assert len(transaction["postings"]) == 2


def test_obligation_query_and_config_hooks_work(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    ids = _seed_accounts()
    _seed_obligations(ids)

    client = TestClient(app, headers=AUTH_HEADERS)
    obligations = client.post(
        "/tools/list_obligations",
        json={"limit": 10, "active_only": True, "correlation_id": "corr-list-ob"},
    )
    assert obligations.status_code == 200
    rows = obligations.json()["obligations"]
    assert [row["name"] for row in rows] == ["Rent", "Utilities"]

    proposal = client.post(
        "/tools/propose_config_change",
        json={
            "source_system": "pytest",
            "external_id": "cfg-1",
            "scope": "runtime_settings",
            "change_payload": {"balance_source_policy": "ledger_only"},
            "correlation_id": "corr-cfg-propose",
        },
    )
    assert proposal.status_code == 200
    proposal_id = proposal.json()["proposal_id"]

    listed = client.post(
        "/tools/list_proposals",
        json={"status": "proposed", "limit": 20, "correlation_id": "corr-list-proposals"},
    )
    assert listed.status_code == 200
    listed_ids = [row["proposal_id"] for row in listed.json()["proposals"]]
    assert proposal_id in listed_ids

    detail = client.post(
        "/tools/get_proposal",
        json={"proposal_id": proposal_id, "correlation_id": "corr-get-proposal"},
    )
    assert detail.status_code == 200
    assert detail.json()["proposal"]["tool_name"] == "propose_config_change"

    approved = client.post(
        "/tools/approve_config_change",
        json={
            "proposal_id": proposal_id,
            "approver_id": "ops-1",
            "reason": "approved",
            "correlation_id": "corr-cfg-approve",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "applied"

    config = client.post(
        "/tools/get_config",
        json={"correlation_id": "corr-get-config"},
    )
    assert config.status_code == 200
    assert set(config.json()["runtime"].keys()) == {"balance_source_policy", "approval_threshold_amount"}


def test_new_read_query_tools_do_not_mutate_canonical_tables(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    ids = _seed_accounts()
    _seed_transactions(ids)
    _seed_obligations(ids)
    client = TestClient(app, headers=AUTH_HEADERS)

    with transaction() as conn:
        before = {
            "transactions": conn.execute("SELECT COUNT(*) AS c FROM ledger_transactions").fetchone()["c"],
            "postings": conn.execute("SELECT COUNT(*) AS c FROM ledger_postings").fetchone()["c"],
            "obligations": conn.execute("SELECT COUNT(*) AS c FROM obligations").fetchone()["c"],
            "proposals": conn.execute("SELECT COUNT(*) AS c FROM approval_proposals").fetchone()["c"],
            "decisions": conn.execute("SELECT COUNT(*) AS c FROM approval_decisions").fetchone()["c"],
            "event_log": conn.execute("SELECT COUNT(*) AS c FROM event_log").fetchone()["c"],
        }

    assert client.post(
        "/tools/list_transactions", json={"limit": 5, "correlation_id": "corr-nowrite-1"}
    ).status_code == 200
    assert client.post(
        "/tools/get_transaction_by_external_id",
        json={"source_system": "pytest", "external_id": "tx-q-1", "correlation_id": "corr-nowrite-2"},
    ).status_code == 200
    assert client.post(
        "/tools/list_obligations", json={"correlation_id": "corr-nowrite-3"}
    ).status_code == 200
    assert client.post(
        "/tools/list_proposals", json={"correlation_id": "corr-nowrite-4"}
    ).status_code == 200
    assert client.post(
        "/tools/get_config", json={"correlation_id": "corr-nowrite-5"}
    ).status_code == 200

    with transaction() as conn:
        after = {
            "transactions": conn.execute("SELECT COUNT(*) AS c FROM ledger_transactions").fetchone()["c"],
            "postings": conn.execute("SELECT COUNT(*) AS c FROM ledger_postings").fetchone()["c"],
            "obligations": conn.execute("SELECT COUNT(*) AS c FROM obligations").fetchone()["c"],
            "proposals": conn.execute("SELECT COUNT(*) AS c FROM approval_proposals").fetchone()["c"],
            "decisions": conn.execute("SELECT COUNT(*) AS c FROM approval_decisions").fetchone()["c"],
            "event_log": conn.execute("SELECT COUNT(*) AS c FROM event_log").fetchone()["c"],
        }

    assert before["transactions"] == after["transactions"]
    assert before["postings"] == after["postings"]
    assert before["obligations"] == after["obligations"]
    assert before["proposals"] == after["proposals"]
    assert before["decisions"] == after["decisions"]
    assert after["event_log"] == before["event_log"] + 5
