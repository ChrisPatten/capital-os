import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import app
from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.schemas.tools import RecordTransactionBundleOut
from tests.support.auth import AUTH_HEADERS


def test_invalid_payload_returns_deterministic_error_shape(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    response = client.post(
        "/tools/create_or_update_obligation",
        json={"source_system": "pytest", "correlation_id": "corr"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "validation_error"
    assert isinstance(detail["details"], list)


def test_compute_posture_invalid_payload_returns_deterministic_error_shape(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    response = client.post(
        "/tools/compute_capital_posture",
        json={"liquidity": "100.00", "correlation_id": "corr"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "validation_error"
    assert isinstance(detail["details"], list)
    assert detail["details"][0]["type"] == "missing"


def test_simulate_spend_invalid_payload_returns_deterministic_error_shape(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    response = client.post(
        "/tools/simulate_spend",
        json={"starting_liquidity": "1000.0000", "correlation_id": "corr"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "validation_error"
    assert isinstance(detail["details"], list)
    assert detail["details"][0]["type"] == "missing"


def test_approve_proposed_transaction_invalid_payload_returns_deterministic_error_shape(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    response = client.post(
        "/tools/approve_proposed_transaction",
        json={"correlation_id": "corr"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "validation_error"
    assert isinstance(detail["details"], list)
    assert detail["details"][0]["type"] == "missing"


def test_reject_proposed_transaction_invalid_payload_returns_deterministic_error_shape(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    response = client.post(
        "/tools/reject_proposed_transaction",
        json={"correlation_id": "corr"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "validation_error"
    assert isinstance(detail["details"], list)
    assert detail["details"][0]["type"] == "missing"


def test_read_query_tools_invalid_payload_returns_deterministic_error_shape(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    response = client.post(
        "/tools/get_account_balances",
        json={"source_policy": "not-a-policy", "correlation_id": "corr-read-invalid"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "validation_error"
    assert isinstance(detail["details"], list)
    assert detail["details"][0]["type"] == "missing"

    cursor_response = client.post(
        "/tools/list_accounts",
        json={"cursor": "not-a-valid-cursor", "correlation_id": "corr-read-invalid-cursor"},
    )
    assert cursor_response.status_code == 422
    cursor_detail = cursor_response.json()["detail"]
    assert cursor_detail["error"] == "validation_error"
    assert isinstance(cursor_detail["details"], list)


def test_reconcile_account_invalid_payload_returns_deterministic_error_shape(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    response = client.post(
        "/tools/reconcile_account",
        json={"account_id": "missing-fields", "correlation_id": "corr-reconcile-invalid"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "validation_error"
    assert isinstance(detail["details"], list)


def test_period_tools_invalid_payload_returns_deterministic_error_shape(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    close_response = client.post(
        "/tools/close_period",
        json={"period_key": "2026-13", "correlation_id": "corr-close-invalid"},
    )
    assert close_response.status_code == 422
    close_detail = close_response.json()["detail"]
    assert close_detail["error"] == "validation_error"
    assert isinstance(close_detail["details"], list)

    lock_response = client.post(
        "/tools/lock_period",
        json={"correlation_id": "corr-lock-invalid"},
    )
    assert lock_response.status_code == 422
    lock_detail = lock_response.json()["detail"]
    assert lock_detail["error"] == "validation_error"
    assert isinstance(lock_detail["details"], list)


def test_query_surface_tools_invalid_payload_returns_deterministic_error_shape(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)

    tx_response = client.post(
        "/tools/list_transactions",
        json={"cursor": "invalid-cursor", "correlation_id": "corr-q-invalid-1"},
    )
    assert tx_response.status_code == 422
    tx_detail = tx_response.json()["detail"]
    assert tx_detail["error"] == "validation_error"
    assert isinstance(tx_detail["details"], list)

    lookup_response = client.post(
        "/tools/get_transaction_by_external_id",
        json={"source_system": "pytest", "correlation_id": "corr-q-invalid-2"},
    )
    assert lookup_response.status_code == 422
    lookup_detail = lookup_response.json()["detail"]
    assert lookup_detail["error"] == "validation_error"
    assert isinstance(lookup_detail["details"], list)

    proposal_response = client.post(
        "/tools/propose_config_change",
        json={"source_system": "pytest", "external_id": "cfg-invalid", "correlation_id": "corr-q-invalid-3"},
    )
    assert proposal_response.status_code == 422
    proposal_detail = proposal_response.json()["detail"]
    assert proposal_detail["error"] == "validation_error"
    assert isinstance(proposal_detail["details"], list)


def test_record_transaction_bundle_backward_compatible_success_contract(db_available, monkeypatch):
    if not db_available:
        pytest.skip("database unavailable")

    from capital_os.config import get_settings

    monkeypatch.setenv("CAPITAL_OS_APPROVAL_THRESHOLD_AMOUNT", "1000.0000")
    get_settings.cache_clear()
    try:
        client = TestClient(app, headers=AUTH_HEADERS)
        with transaction() as conn:
            debit = create_account(conn, {"code": "8810", "name": "Contract Debit", "account_type": "asset"})
            credit = create_account(conn, {"code": "8811", "name": "Contract Credit", "account_type": "liability"})

        committed = client.post(
            "/tools/record_transaction_bundle",
            json={
                "source_system": "pytest",
                "external_id": "contract-committed-1",
                "date": "2026-01-01T00:00:00Z",
                "description": "contract committed",
                "postings": [
                    {"account_id": debit, "amount": "10.0000", "currency": "USD"},
                    {"account_id": credit, "amount": "-10.0000", "currency": "USD"},
                ],
                "correlation_id": "corr-contract-committed-1",
            },
        )
        assert committed.status_code == 200
        committed_body = committed.json()
        assert committed_body["status"] == "committed"
        assert committed_body["transaction_id"]
        assert isinstance(committed_body["posting_ids"], list)
        assert committed_body["correlation_id"] == "corr-contract-committed-1"
        assert committed_body["output_hash"]
        assert committed_body["proposal_id"] is None
        assert committed_body["proposed_transaction"] is None
        assert committed_body["matched_transactions"] == []
        assert committed_body["match_reason"] is None

        proposed = client.post(
            "/tools/record_transaction_bundle",
            json={
                "source_system": "pytest",
                "external_id": "contract-proposed-1",
                "date": "2026-01-01T08:00:00Z",
                "description": "contract proposed",
                "postings": [
                    {"account_id": debit, "amount": "10.00004", "currency": "USD"},
                    {"account_id": credit, "amount": "-10.0000", "currency": "USD"},
                ],
                "correlation_id": "corr-contract-proposed-1",
            },
        )
        assert proposed.status_code == 200
        proposed_body = proposed.json()
        assert proposed_body["status"] == "proposed"
        assert proposed_body["proposal_id"]
        assert proposed_body["required_approvals"] >= 1
        assert proposed_body["approvals_received"] == 0
        assert proposed_body["correlation_id"] == "corr-contract-proposed-1"
        assert proposed_body["output_hash"]
        assert proposed_body["transaction_id"] is None
        assert proposed_body["posting_ids"] == []
        assert proposed_body["proposed_transaction"]["external_id"] == "contract-proposed-1"
        assert proposed_body["matched_transactions"]
        assert proposed_body["match_reason"] == "same_account_date_amount"
    finally:
        get_settings.cache_clear()


def test_duplicate_risk_proposal_payload_persistence_matches_response(db_available, monkeypatch):
    if not db_available:
        pytest.skip("database unavailable")

    from capital_os.config import get_settings

    monkeypatch.setenv("CAPITAL_OS_APPROVAL_THRESHOLD_AMOUNT", "1000.0000")
    get_settings.cache_clear()
    try:
        client = TestClient(app, headers=AUTH_HEADERS)
        with transaction() as conn:
            debit = create_account(conn, {"code": "8820", "name": "Persist Debit", "account_type": "asset"})
            credit = create_account(conn, {"code": "8821", "name": "Persist Credit", "account_type": "liability"})

        seed = client.post(
            "/tools/record_transaction_bundle",
            json={
                "source_system": "pytest",
                "external_id": "persist-seed-1",
                "date": "2026-01-01T00:00:00Z",
                "description": "persist seed",
                "postings": [
                    {"account_id": debit, "amount": "12.0000", "currency": "USD"},
                    {"account_id": credit, "amount": "-12.0000", "currency": "USD"},
                ],
                "correlation_id": "corr-persist-seed-1",
            },
        )
        assert seed.status_code == 200

        proposed = client.post(
            "/tools/record_transaction_bundle",
            json={
                "source_system": "pytest",
                "external_id": "persist-candidate-1",
                "date": "2026-01-01T07:00:00Z",
                "description": "persist candidate",
                "postings": [
                    {"account_id": debit, "amount": "12.00004", "currency": "USD"},
                    {"account_id": credit, "amount": "-12.0000", "currency": "USD"},
                ],
                "correlation_id": "corr-persist-candidate-1",
            },
        )
        assert proposed.status_code == 200
        body = proposed.json()
        assert body["status"] == "proposed"

        with transaction() as conn:
            row = conn.execute(
                """
                SELECT response_payload, output_hash
                FROM approval_proposals
                WHERE source_system='pytest' AND external_id='persist-candidate-1'
                """
            ).fetchone()

        assert row is not None
        assert row["response_payload"] is not None
        import json
        persisted_payload = json.loads(row["response_payload"])
        normalized_persisted = RecordTransactionBundleOut.model_validate(persisted_payload).model_dump(mode="json")
        normalized_response = RecordTransactionBundleOut.model_validate(body).model_dump(mode="json")
        assert normalized_persisted == normalized_response
        assert row["output_hash"] == body["output_hash"]
    finally:
        get_settings.cache_clear()
