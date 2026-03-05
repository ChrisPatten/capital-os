from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import app
from capital_os.db.session import transaction
from tests.support.auth import AUTH_HEADERS


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


def test_update_account_profile_validation_failure_is_event_logged(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    account_id = _create_account(client, "prof-sec-1000")
    response = client.post(
        "/tools/update_account_profile",
        headers={"x-correlation-id": "corr-prof-sec-validation"},
        json={
            "account_id": account_id,
            "source_system": "pytest",
            "external_id": "prof-sec-ext-1",
            "correlation_id": "corr-prof-sec-validation",
        },
    )
    assert response.status_code == 422

    with transaction() as conn:
        row = conn.execute(
            """
            SELECT status, error_code
            FROM event_log
            WHERE tool_name='update_account_profile' AND correlation_id=?
            """,
            ("corr-prof-sec-validation",),
        ).fetchone()

    assert row is not None
    assert row["status"] == "validation_error"
    assert row["error_code"] == "validation_error"


def test_update_account_profile_concurrent_duplicate_requests_are_retry_safe(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    account_id = _create_account(client, "prof-sec-1001")

    payload = {
        "account_id": account_id,
        "display_name": "Concurrent Rename",
        "institution_suffix": "CC-01",
        "source_system": "pytest",
        "external_id": "prof-sec-concurrent-ext",
    }

    def _call(correlation_id: str):
        local_client = TestClient(app, headers=AUTH_HEADERS)
        return local_client.post(
            "/tools/update_account_profile",
            headers={"x-correlation-id": correlation_id},
            json={**payload, "correlation_id": correlation_id},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                _call,
                ["corr-prof-sec-concurrent-1", "corr-prof-sec-concurrent-2"],
            )
        )

    assert all(response.status_code == 200 for response in responses)
    bodies = [response.json() for response in responses]
    assert bodies[0] == bodies[1]

    with transaction() as conn:
        proposal_count = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM approval_proposals
            WHERE tool_name='update_account_profile'
              AND source_system='pytest'
              AND external_id='prof-sec-concurrent-ext'
            """
        ).fetchone()["c"]
        history_count = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM account_identifier_history
            WHERE account_id=? AND source_system='pytest'
            """,
            (account_id,),
        ).fetchone()["c"]
        account_row = conn.execute(
            "SELECT name FROM accounts WHERE account_id=?",
            (account_id,),
        ).fetchone()

    assert proposal_count == 1
    assert history_count == 1
    assert account_row is not None
    assert account_row["name"] == "Concurrent Rename"
