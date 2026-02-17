import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import app
from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account
from tests.support.auth import AUTH_HEADERS, READ_ONLY_AUTH_HEADERS


@pytest.fixture
def client():
    return TestClient(app, headers=AUTH_HEADERS)


def test_create_account_happy_path_asset(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    payload = {
        "code": "1400",
        "name": "New Cash Account",
        "account_type": "asset",
        "correlation_id": "corr-create-acct-1",
    }
    resp = client.post("/tools/create_account", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "committed"
    assert body["account_id"]
    assert body["correlation_id"] == "corr-create-acct-1"
    assert body["output_hash"]


def test_create_account_all_types(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    for i, acct_type in enumerate(["asset", "liability", "equity", "income", "expense"]):
        payload = {
            "code": f"type-test-{i}",
            "name": f"Test {acct_type}",
            "account_type": acct_type,
            "correlation_id": f"corr-type-{i}",
        }
        resp = client.post("/tools/create_account", json=payload)
        assert resp.status_code == 200, f"Failed for {acct_type}: {resp.json()}"
        assert resp.json()["status"] == "committed"


def test_create_account_with_parent(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    parent_resp = client.post("/tools/create_account", json={
        "code": "parent-1000",
        "name": "Parent Assets",
        "account_type": "asset",
        "correlation_id": "corr-parent-1",
    })
    assert parent_resp.status_code == 200
    parent_id = parent_resp.json()["account_id"]

    child_resp = client.post("/tools/create_account", json={
        "code": "child-1100",
        "name": "Child Checking",
        "account_type": "asset",
        "parent_account_id": parent_id,
        "correlation_id": "corr-child-1",
    })
    assert child_resp.status_code == 200
    assert child_resp.json()["status"] == "committed"


def test_create_account_with_metadata(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    payload = {
        "code": "meta-acct",
        "name": "Account With Metadata",
        "account_type": "asset",
        "metadata": {"currency": "USD", "institution": "Chase"},
        "correlation_id": "corr-meta-1",
    }
    resp = client.post("/tools/create_account", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "committed"


def test_create_account_duplicate_code_rejected(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    payload = {
        "code": "dup-code",
        "name": "First Account",
        "account_type": "asset",
        "correlation_id": "corr-dup-1",
    }
    resp1 = client.post("/tools/create_account", json=payload)
    assert resp1.status_code == 200

    payload2 = {
        "code": "dup-code",
        "name": "Second Account Same Code",
        "account_type": "liability",
        "correlation_id": "corr-dup-2",
    }
    resp2 = client.post("/tools/create_account", json=payload2)
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"]["message"]


def test_create_account_nonexistent_parent_rejected(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    payload = {
        "code": "orphan-acct",
        "name": "Orphan",
        "account_type": "asset",
        "parent_account_id": "nonexistent-parent-id",
        "correlation_id": "corr-orphan-1",
    }
    resp = client.post("/tools/create_account", json=payload)
    assert resp.status_code == 400
    assert "parent_account_id" in resp.json()["detail"]["message"]


def test_create_account_nonexistent_entity_rejected(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    payload = {
        "code": "bad-entity-acct",
        "name": "Bad Entity",
        "account_type": "asset",
        "entity_id": "nonexistent-entity",
        "correlation_id": "corr-entity-1",
    }
    resp = client.post("/tools/create_account", json=payload)
    assert resp.status_code == 400
    assert "entity_id" in resp.json()["detail"]["message"]


def test_create_account_cycle_rejected(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    resp_a = client.post("/tools/create_account", json={
        "code": "cycle-a",
        "name": "Cycle A",
        "account_type": "asset",
        "correlation_id": "corr-cycle-a",
    })
    assert resp_a.status_code == 200
    id_a = resp_a.json()["account_id"]

    resp_b = client.post("/tools/create_account", json={
        "code": "cycle-b",
        "name": "Cycle B",
        "account_type": "asset",
        "parent_account_id": id_a,
        "correlation_id": "corr-cycle-b",
    })
    assert resp_b.status_code == 200
    id_b = resp_b.json()["account_id"]

    # Try to make A a child of B (cycle: A->B->A)
    with pytest.raises(Exception):
        with transaction() as conn:
            conn.execute(
                "UPDATE accounts SET parent_account_id=? WHERE account_id=?",
                (id_b, id_a),
            )


def test_create_account_missing_required_fields(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    # Missing code
    resp = client.post("/tools/create_account", json={
        "name": "No Code",
        "account_type": "asset",
        "correlation_id": "corr-missing-1",
    })
    assert resp.status_code == 422

    # Missing name
    resp = client.post("/tools/create_account", json={
        "code": "no-name",
        "account_type": "asset",
        "correlation_id": "corr-missing-2",
    })
    assert resp.status_code == 422

    # Missing account_type
    resp = client.post("/tools/create_account", json={
        "code": "no-type",
        "name": "No Type",
        "correlation_id": "corr-missing-3",
    })
    assert resp.status_code == 422


def test_create_account_invalid_account_type(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    resp = client.post("/tools/create_account", json={
        "code": "bad-type",
        "name": "Bad Type",
        "account_type": "savings",
        "correlation_id": "corr-badtype-1",
    })
    assert resp.status_code == 422


def test_create_account_extra_fields_rejected(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    resp = client.post("/tools/create_account", json={
        "code": "extra-field",
        "name": "Extra",
        "account_type": "asset",
        "correlation_id": "corr-extra-1",
        "unknown_field": "should fail",
    })
    assert resp.status_code == 422


def test_create_account_missing_correlation_id(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    resp = client.post("/tools/create_account", json={
        "code": "no-corr",
        "name": "No Correlation",
        "account_type": "asset",
    })
    assert resp.status_code == 422


def test_create_account_auth_required(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app)
    resp = client.post("/tools/create_account", json={
        "code": "no-auth",
        "name": "No Auth",
        "account_type": "asset",
        "correlation_id": "corr-noauth-1",
    })
    assert resp.status_code == 401


def test_create_account_reader_token_forbidden(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=READ_ONLY_AUTH_HEADERS)
    resp = client.post("/tools/create_account", json={
        "code": "reader-acct",
        "name": "Reader Account",
        "account_type": "asset",
        "correlation_id": "corr-reader-1",
    })
    assert resp.status_code == 403


def test_create_account_event_logged(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    resp = client.post("/tools/create_account", json={
        "code": "event-logged-acct",
        "name": "Event Logged",
        "account_type": "asset",
        "correlation_id": "corr-eventlog-1",
    })
    assert resp.status_code == 200
    body = resp.json()

    with transaction() as conn:
        row = conn.execute(
            "SELECT * FROM event_log WHERE tool_name='create_account' AND correlation_id=?",
            ("corr-eventlog-1",),
        ).fetchone()

    assert row is not None
    assert row["output_hash"] == body["output_hash"]
    assert row["input_hash"]
    assert row["status"] == "ok"
