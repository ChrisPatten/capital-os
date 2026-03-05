import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import app
from capital_os.db.session import transaction
from tests.support.auth import AUTH_HEADERS, READ_ONLY_AUTH_HEADERS


@pytest.fixture
def client():
    return TestClient(app, headers=AUTH_HEADERS)


def _create_account(client: TestClient, code: str) -> str:
    response = client.post(
        "/tools/create_account",
        json={
            "code": code,
            "name": f"Account {code}",
            "account_type": "asset",
            "correlation_id": f"corr-create-{code}",
        },
    )
    assert response.status_code == 200
    return response.json()["account_id"]


def _request_headers(correlation_id: str) -> dict[str, str]:
    return {**AUTH_HEADERS, "x-correlation-id": correlation_id}


def test_update_account_profile_happy_path(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    account_id = _create_account(client, "prof-1000")
    response = client.post(
        "/tools/update_account_profile",
        headers=_request_headers("corr-profile-1"),
        json={
            "account_id": account_id,
            "display_name": "Primary Checking",
            "institution_name": "River Credit Union",
            "institution_suffix": "SFX-77",
            "source_system": "pytest",
            "external_id": "profile-1",
            "correlation_id": "corr-profile-1",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["account_id"] == account_id
    assert body["display_name"] == "Primary Checking"
    assert body["institution_name"] == "River Credit Union"
    assert body["institution_suffix"] == "SFX-77"
    assert body["status"] == "committed"
    assert body["correlation_id"] == "corr-profile-1"
    assert body["output_hash"]

    with transaction() as conn:
        account_row = conn.execute(
            "SELECT name, metadata FROM accounts WHERE account_id=?",
            (account_id,),
        ).fetchone()
        event_row = conn.execute(
            "SELECT output_hash, status FROM event_log WHERE tool_name='update_account_profile' AND correlation_id=?",
            ("corr-profile-1",),
        ).fetchone()

    assert account_row is not None
    assert account_row["name"] == "Primary Checking"
    assert '"institution_name":"River Credit Union"' in account_row["metadata"]
    assert '"institution_suffix":"SFX-77"' in account_row["metadata"]
    assert event_row is not None
    assert event_row["status"] == "ok"
    assert event_row["output_hash"] == body["output_hash"]


def test_update_account_profile_requires_mutable_field(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    account_id = _create_account(client, "prof-1001")
    response = client.post(
        "/tools/update_account_profile",
        headers=_request_headers("corr-profile-2"),
        json={
            "account_id": account_id,
            "source_system": "pytest",
            "external_id": "profile-2",
            "correlation_id": "corr-profile-2",
        },
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "validation_error"


def test_update_account_profile_missing_account_returns_400(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    response = client.post(
        "/tools/update_account_profile",
        headers=_request_headers("corr-profile-3"),
        json={
            "account_id": "missing-account",
            "display_name": "Renamed",
            "source_system": "pytest",
            "external_id": "profile-3",
            "correlation_id": "corr-profile-3",
        },
    )
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]["message"]


def test_update_account_profile_requires_auth_and_write_capability(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    no_auth_client = TestClient(app)
    no_auth = no_auth_client.post(
        "/tools/update_account_profile",
        json={"correlation_id": "corr-no-auth"},
    )
    assert no_auth.status_code == 401

    reader_client = TestClient(app, headers=READ_ONLY_AUTH_HEADERS)
    forbidden = reader_client.post(
        "/tools/update_account_profile",
        headers={"x-correlation-id": "corr-reader-authz"},
        json={"correlation_id": "corr-reader-authz"},
    )
    assert forbidden.status_code == 403


def test_update_account_profile_requires_correlation_id(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    account_id = _create_account(client, "prof-1002")
    response = client.post(
        "/tools/update_account_profile",
        headers={"x-correlation-id": "corr-profile-4"},
        json={
            "account_id": account_id,
            "display_name": "Updated Name",
            "source_system": "pytest",
            "external_id": "profile-4",
        },
    )
    assert response.status_code == 422


def test_update_account_profile_idempotent_replay_returns_canonical_result(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    account_id = _create_account(client, "prof-1003")
    first = client.post(
        "/tools/update_account_profile",
        headers=_request_headers("corr-profile-idem-first"),
        json={
            "account_id": account_id,
            "display_name": "CU Checking 01",
            "institution_suffix": "001A",
            "source_system": "pytest",
            "external_id": "profile-idempotent-1",
            "correlation_id": "corr-profile-idem-first",
        },
    )
    assert first.status_code == 200
    first_body = first.json()

    second = client.post(
        "/tools/update_account_profile",
        headers=_request_headers("corr-profile-idem-second"),
        json={
            "account_id": account_id,
            "display_name": "SHOULD NOT APPLY",
            "institution_suffix": "SHOULD-NOT-APPLY",
            "source_system": "pytest",
            "external_id": "profile-idempotent-1",
            "correlation_id": "corr-profile-idem-second",
        },
    )
    assert second.status_code == 200
    second_body = second.json()
    assert second_body == first_body

    with transaction() as conn:
        account_row = conn.execute(
            "SELECT name, metadata FROM accounts WHERE account_id=?",
            (account_id,),
        ).fetchone()
        proposal_count = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM approval_proposals
            WHERE tool_name='update_account_profile' AND source_system='pytest' AND external_id='profile-idempotent-1'
            """
        ).fetchone()["c"]
        replay_event = conn.execute(
            """
            SELECT output_hash, status
            FROM event_log
            WHERE tool_name='update_account_profile' AND correlation_id=?
            """,
            ("corr-profile-idem-second",),
        ).fetchone()

    assert account_row is not None
    assert account_row["name"] == "CU Checking 01"
    assert '"institution_suffix":"001A"' in account_row["metadata"]
    assert proposal_count == 1
    assert replay_event is not None
    assert replay_event["status"] == "ok"
    assert replay_event["output_hash"] == first_body["output_hash"]


def test_update_account_profile_requires_correlation_header(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    account_id = _create_account(client, "prof-1004")
    response = client.post(
        "/tools/update_account_profile",
        json={
            "account_id": account_id,
            "display_name": "Header Missing",
            "source_system": "pytest",
            "external_id": "profile-5",
            "correlation_id": "corr-profile-5",
        },
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "validation_error"


def test_update_account_profile_rejects_mismatched_correlation_header(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    account_id = _create_account(client, "prof-1005")
    response = client.post(
        "/tools/update_account_profile",
        headers={"x-correlation-id": "corr-profile-6-header"},
        json={
            "account_id": account_id,
            "display_name": "Header Mismatch",
            "source_system": "pytest",
            "external_id": "profile-6",
            "correlation_id": "corr-profile-6-body",
        },
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "validation_error"
