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
