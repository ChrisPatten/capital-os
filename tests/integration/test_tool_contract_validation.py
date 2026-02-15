import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import app


def test_invalid_payload_returns_deterministic_error_shape(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app)
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

    client = TestClient(app)
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

    client = TestClient(app)
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

    client = TestClient(app)
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

    client = TestClient(app)
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

    client = TestClient(app)
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

    client = TestClient(app)
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

    client = TestClient(app)
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

    client = TestClient(app)

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
