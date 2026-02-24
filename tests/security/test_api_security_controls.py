from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import TOOL_HANDLERS, app
from capital_os.config import get_settings
from capital_os.db.session import transaction
from tests.support.auth import AUTH_HEADERS, READ_ONLY_AUTH_HEADERS


def test_health_route_remains_unauthenticated(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200


def test_health_route_missing_db_does_not_create_file(monkeypatch, tmp_path: Path):
    missing_db = tmp_path / "ledger.db"
    monkeypatch.setenv("CAPITAL_OS_DB_URL", f"sqlite:///{missing_db}")
    get_settings.cache_clear()
    try:
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 503
        assert response.json()["detail"]["status"] == "down"
        assert not missing_db.exists()
    finally:
        get_settings.cache_clear()


def test_tools_reject_missing_authentication_and_log_event(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app)
    payload = {"correlation_id": "corr-auth-required"}
    response = client.post("/tools/list_accounts", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == {"error": "authentication_required"}

    with transaction() as conn:
        row = conn.execute(
            """
            SELECT status, error_code, authorization_result, actor_id, authn_method
            FROM event_log
            WHERE tool_name = 'list_accounts' AND correlation_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (payload["correlation_id"],),
        ).fetchone()
    assert row is not None
    assert row["status"] == "auth_error"
    assert row["error_code"] == "authentication_required"
    assert row["authorization_result"] == "denied"
    assert row["actor_id"] is None
    assert row["authn_method"] is None


def test_authorization_denial_is_deterministic_and_logged(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=READ_ONLY_AUTH_HEADERS)
    payload = {"correlation_id": "corr-authz-denied"}
    response = client.post("/tools/record_balance_snapshot", json=payload)
    assert response.status_code == 403
    assert response.json()["detail"] == {"error": "forbidden"}

    with transaction() as conn:
        row = conn.execute(
            """
            SELECT status, error_code, authorization_result, actor_id, authn_method
            FROM event_log
            WHERE tool_name = 'record_balance_snapshot' AND correlation_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (payload["correlation_id"],),
        ).fetchone()
    assert row is not None
    assert row["status"] == "authz_denied"
    assert row["error_code"] == "forbidden"
    assert row["authorization_result"] == "denied"
    assert row["actor_id"] == "actor-reader"
    assert row["authn_method"] == "header_token"


def test_correlation_id_is_mandatory_and_logged(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    response = client.post("/tools/list_accounts", json={})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "validation_error"
    assert detail["details"][0]["loc"] == ["body", "correlation_id"]

    with transaction() as conn:
        row = conn.execute(
            """
            SELECT status, error_code, authorization_result, actor_id
            FROM event_log
            WHERE tool_name = 'list_accounts'
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()
    assert row is not None
    assert row["status"] == "validation_error"
    assert row["error_code"] == "validation_error"
    assert row["authorization_result"] == "denied"
    assert row["actor_id"] == "actor-admin"


def test_tool_surface_has_authn_and_authz_coverage(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app)
    reader_client = TestClient(app, headers=READ_ONLY_AUTH_HEADERS)
    tool_capabilities = get_settings().tool_capabilities or {}

    for tool_name in sorted(TOOL_HANDLERS):
        missing_auth = client.post(f"/tools/{tool_name}", json={"correlation_id": f"corr-no-auth-{tool_name}"})
        assert missing_auth.status_code == 401, tool_name

        required_capability = tool_capabilities.get(tool_name)
        reader_response = reader_client.post(
            f"/tools/{tool_name}",
            json={"correlation_id": f"corr-reader-{tool_name}"},
        )
        if required_capability == "tools:read":
            assert reader_response.status_code != 403, tool_name
        else:
            assert reader_response.status_code == 403, tool_name
