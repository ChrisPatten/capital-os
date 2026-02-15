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


def test_compute_posture_success_and_validation_failures_logged(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app)
    ok_payload = {
        "liquidity": "50000.0000",
        "fixed_burn": "12000.0000",
        "variable_burn": "3500.0000",
        "minimum_reserve": "30000.0000",
        "volatility_buffer": "5000.0000",
        "correlation_id": "corr-posture-1",
    }
    bad_payload = {"liquidity": "100.00", "correlation_id": "corr-posture-2"}

    response = client.post("/tools/compute_capital_posture", json=ok_payload)
    assert response.status_code == 200
    body = response.json()
    assert body["correlation_id"] == "corr-posture-1"
    assert body["risk_band"] == "guarded"
    assert list(body["explanation"].keys()) == ["contributing_balances", "reserve_assumptions"]
    assert isinstance(body["output_hash"], str)

    assert client.post("/tools/compute_capital_posture", json=bad_payload).status_code == 422

    with transaction() as conn:
        rows = conn.execute(
            """
            SELECT tool_name, correlation_id, input_hash, output_hash, event_timestamp, duration_ms, status
            FROM event_log
            WHERE tool_name='compute_capital_posture'
            ORDER BY created_at
            """
        ).fetchall()
    assert len(rows) == 2
    assert rows[0]["status"] == "ok"
    assert rows[0]["correlation_id"] == "corr-posture-1"
    assert rows[0]["input_hash"]
    assert rows[0]["output_hash"]
    assert rows[0]["event_timestamp"]
    assert rows[0]["duration_ms"] >= 0
    assert rows[1]["status"] == "validation_error"
    assert rows[1]["correlation_id"] == "corr-posture-2"
    assert rows[1]["input_hash"]
    assert rows[1]["output_hash"]
    assert rows[1]["event_timestamp"]
    assert rows[1]["duration_ms"] >= 0


def test_compute_posture_output_hash_is_deterministic(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app)
    payload = {
        "liquidity": "50000.0000",
        "fixed_burn": "12000.0000",
        "variable_burn": "3500.0000",
        "minimum_reserve": "30000.0000",
        "volatility_buffer": "5000.0000",
        "correlation_id": "corr-posture-stable",
    }
    first = client.post("/tools/compute_capital_posture", json=payload)
    second = client.post("/tools/compute_capital_posture", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["output_hash"] == second.json()["output_hash"]


def test_simulate_spend_success_and_validation_failures_logged(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app)
    ok_payload = {
        "starting_liquidity": "5000.0000",
        "start_date": "2026-01-01",
        "horizon_periods": 3,
        "spends": [
            {"spend_id": "ot-1", "amount": "250.0000", "type": "one_time", "spend_date": "2026-02-01"},
            {
                "spend_id": "rc-1",
                "amount": "100.0000",
                "type": "recurring",
                "start_date": "2026-01-10",
                "cadence": "monthly",
                "occurrences": 2,
            },
        ],
        "correlation_id": "corr-sim-1",
    }
    bad_payload = {"starting_liquidity": "1000.0000", "correlation_id": "corr-sim-2"}

    ok_response = client.post("/tools/simulate_spend", json=ok_payload)
    assert ok_response.status_code == 200
    assert ok_response.json()["correlation_id"] == "corr-sim-1"
    assert isinstance(ok_response.json()["output_hash"], str)

    assert client.post("/tools/simulate_spend", json=bad_payload).status_code == 422

    with transaction() as conn:
        rows = conn.execute(
            """
            SELECT tool_name, correlation_id, input_hash, output_hash, event_timestamp, duration_ms, status
            FROM event_log
            WHERE tool_name='simulate_spend'
            ORDER BY created_at
            """
        ).fetchall()

    assert len(rows) == 2
    assert rows[0]["status"] == "ok"
    assert rows[0]["correlation_id"] == "corr-sim-1"
    assert rows[0]["input_hash"]
    assert rows[0]["output_hash"]
    assert rows[0]["event_timestamp"]
    assert rows[0]["duration_ms"] >= 0
    assert rows[1]["status"] == "validation_error"
    assert rows[1]["correlation_id"] == "corr-sim-2"
    assert rows[1]["input_hash"]
    assert rows[1]["output_hash"]
    assert rows[1]["event_timestamp"]
    assert rows[1]["duration_ms"] >= 0


def test_simulate_spend_output_hash_is_deterministic(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app)
    payload = {
        "starting_liquidity": "5000.0000",
        "start_date": "2026-01-01",
        "horizon_periods": 2,
        "spends": [
            {"spend_id": "ot-1", "amount": "50.0000", "type": "one_time", "spend_date": "2026-01-12"},
            {
                "spend_id": "rc-1",
                "amount": "25.0000",
                "type": "recurring",
                "start_date": "2026-01-06",
                "cadence": "weekly",
                "occurrences": 4,
            },
        ],
        "correlation_id": "corr-sim-stable",
    }
    first = client.post("/tools/simulate_spend", json=payload)
    second = client.post("/tools/simulate_spend", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["output_hash"] == second.json()["output_hash"]


def test_approval_tools_success_and_validation_failures_logged(db_available, monkeypatch):
    if not db_available:
        pytest.skip("database unavailable")

    from capital_os.config import get_settings

    monkeypatch.setenv("CAPITAL_OS_APPROVAL_THRESHOLD_AMOUNT", "100.0000")
    get_settings.cache_clear()

    client = TestClient(app)
    with transaction() as conn:
        a1 = create_account(conn, {"code": "1700", "name": "Approval Cash", "account_type": "asset"})
        a2 = create_account(conn, {"code": "2700", "name": "Approval Liability", "account_type": "liability"})

    proposed = client.post(
        "/tools/record_transaction_bundle",
        json={
            "source_system": "pytest",
            "external_id": "evt-approval-1",
            "date": "2026-01-01T00:00:00Z",
            "description": "proposal",
            "postings": [
                {"account_id": a1, "amount": "250.0000", "currency": "USD"},
                {"account_id": a2, "amount": "-250.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-propose-evt",
        },
    )
    assert proposed.status_code == 200
    proposal_id = proposed.json()["proposal_id"]

    approve_ok = client.post(
        "/tools/approve_proposed_transaction",
        json={
            "proposal_id": proposal_id,
            "reason": "approved",
            "correlation_id": "corr-approve-evt-1",
        },
    )
    assert approve_ok.status_code == 200

    approve_bad = client.post("/tools/approve_proposed_transaction", json={"correlation_id": "corr-approve-evt-2"})
    assert approve_bad.status_code == 422

    reject_bad = client.post("/tools/reject_proposed_transaction", json={"correlation_id": "corr-reject-evt-1"})
    assert reject_bad.status_code == 422

    with transaction() as conn:
        approve_rows = conn.execute(
            """
            SELECT correlation_id, status, input_hash, output_hash
            FROM event_log
            WHERE tool_name='approve_proposed_transaction'
            ORDER BY created_at
            """
        ).fetchall()
        reject_rows = conn.execute(
            """
            SELECT correlation_id, status, input_hash, output_hash
            FROM event_log
            WHERE tool_name='reject_proposed_transaction'
            ORDER BY created_at
            """
        ).fetchall()

    assert len(approve_rows) == 2
    assert approve_rows[0]["status"] == "ok"
    assert approve_rows[0]["correlation_id"] == "corr-approve-evt-1"
    assert approve_rows[0]["input_hash"]
    assert approve_rows[0]["output_hash"]
    assert approve_rows[1]["status"] == "validation_error"
    assert approve_rows[1]["correlation_id"] == "corr-approve-evt-2"
    assert approve_rows[1]["input_hash"]
    assert approve_rows[1]["output_hash"]

    assert len(reject_rows) == 1
    assert reject_rows[0]["status"] == "validation_error"
    assert reject_rows[0]["correlation_id"] == "corr-reject-evt-1"
    assert reject_rows[0]["input_hash"]
    assert reject_rows[0]["output_hash"]
    get_settings.cache_clear()


def test_read_query_tools_success_and_validation_failures_logged(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app)
    with transaction() as conn:
        create_account(conn, {"code": "1000", "name": "Cash", "account_type": "asset"})

    assert (
        client.post(
            "/tools/list_accounts",
            json={"limit": 5, "correlation_id": "corr-read-evt-ok"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/tools/list_accounts",
            json={"limit": 5},
        ).status_code
        == 422
    )

    with transaction() as conn:
        rows = conn.execute(
            """
            SELECT correlation_id, status, input_hash, output_hash
            FROM event_log
            WHERE tool_name='list_accounts'
            ORDER BY created_at
            """
        ).fetchall()

    assert len(rows) == 2
    assert rows[0]["status"] == "ok"
    assert rows[0]["correlation_id"] == "corr-read-evt-ok"
    assert rows[0]["input_hash"]
    assert rows[0]["output_hash"]
    assert rows[1]["status"] == "validation_error"
    assert rows[1]["correlation_id"] == "unknown"
    assert rows[1]["input_hash"]
    assert rows[1]["output_hash"]


def test_reconcile_account_success_and_validation_failures_logged(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app)
    with transaction() as conn:
        account_id = create_account(conn, {"code": "4100", "name": "Recon", "account_type": "asset"})

    assert (
        client.post(
            "/tools/reconcile_account",
            json={
                "account_id": account_id,
                "as_of_date": "2026-01-10",
                "method": "best_available",
                "correlation_id": "corr-recon-evt-ok",
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/tools/reconcile_account",
            json={"account_id": account_id, "correlation_id": "corr-recon-evt-invalid"},
        ).status_code
        == 422
    )

    with transaction() as conn:
        rows = conn.execute(
            """
            SELECT correlation_id, status, input_hash, output_hash
            FROM event_log
            WHERE tool_name='reconcile_account'
            ORDER BY created_at
            """
        ).fetchall()

    assert len(rows) == 2
    assert rows[0]["status"] == "ok"
    assert rows[0]["correlation_id"] == "corr-recon-evt-ok"
    assert rows[0]["input_hash"]
    assert rows[0]["output_hash"]
    assert rows[1]["status"] == "validation_error"
    assert rows[1]["correlation_id"] == "corr-recon-evt-invalid"
    assert rows[1]["input_hash"]
    assert rows[1]["output_hash"]
