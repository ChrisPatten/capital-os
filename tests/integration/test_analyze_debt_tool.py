from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import app
from tests.support.auth import AUTH_HEADERS
from capital_os.db.session import transaction


def _valid_payload(correlation_id: str) -> dict:
    return {
        "liabilities": [
            {
                "liability_id": "loan-credit-card",
                "current_balance": "4200.0000",
                "apr": "22.0000",
                "minimum_payment": "130.0000",
            },
            {
                "liability_id": "loan-auto",
                "current_balance": "10500.0000",
                "apr": "7.2500",
                "minimum_payment": "320.0000",
            },
        ],
        "optional_payoff_amount": "1200.0000",
        "reserve_floor": "2500.0000",
        "correlation_id": correlation_id,
    }


def test_analyze_debt_contract_validation_failure_shape(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    response = client.post("/tools/analyze_debt", json={"correlation_id": "corr-debt-invalid"})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "validation_error"
    assert isinstance(detail["details"], list)
    assert detail["details"][0]["type"] == "missing"


def test_analyze_debt_success_and_validation_event_logs(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    ok_payload = _valid_payload("corr-debt-1")
    bad_payload = {
        "liabilities": [
            {
                "liability_id": "loan-1",
                "current_balance": "1000.0000",
                "apr": "15.0000",
                "minimum_payment": "40.0000",
                "secret_token": "super-secret-123",
            }
        ],
        "correlation_id": "corr-debt-2",
    }

    ok_response = client.post("/tools/analyze_debt", json=ok_payload)
    assert ok_response.status_code == 200
    ok_body = ok_response.json()
    assert ok_body["correlation_id"] == "corr-debt-1"
    assert isinstance(ok_body["output_hash"], str)
    assert "secret_token" not in ok_response.text

    bad_response = client.post("/tools/analyze_debt", json=bad_payload)
    assert bad_response.status_code == 422
    assert "super-secret-123" not in bad_response.text

    with transaction() as conn:
        rows = conn.execute(
            """
            SELECT correlation_id, input_hash, output_hash, status, error_message
            FROM event_log
            WHERE tool_name = 'analyze_debt'
            ORDER BY created_at
            """
        ).fetchall()

    assert len(rows) == 2
    assert rows[0]["status"] == "ok"
    assert rows[0]["correlation_id"] == "corr-debt-1"
    assert rows[0]["input_hash"]
    assert rows[0]["output_hash"]
    assert rows[0]["error_message"] is None

    assert rows[1]["status"] == "validation_error"
    assert rows[1]["correlation_id"] == "corr-debt-2"
    assert rows[1]["input_hash"]
    assert rows[1]["output_hash"]
    assert rows[1]["error_message"] == "validation_error"


def test_analyze_debt_output_hash_deterministic(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    payload = _valid_payload("corr-debt-stable")
    first = client.post("/tools/analyze_debt", json=payload)
    second = client.post("/tools/analyze_debt", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["output_hash"] == second.json()["output_hash"]


def test_analyze_debt_rejects_secret_like_liability_identifier(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    response = client.post(
        "/tools/analyze_debt",
        json={
            "liabilities": [
                {
                    "liability_id": "customer-secret-token",
                    "current_balance": "1000.0000",
                    "apr": "15.0000",
                    "minimum_payment": "40.0000",
                }
            ],
            "correlation_id": "corr-debt-secret-id",
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "validation_error"
    assert "customer-secret-token" not in response.text
