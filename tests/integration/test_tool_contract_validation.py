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
        json={"as_of_date": "2026-01-10", "correlation_id": "corr-read-invalid"},
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
