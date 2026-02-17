import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import app
from capital_os.db.session import transaction
from tests.support.auth import AUTH_HEADERS, READ_ONLY_AUTH_HEADERS


@pytest.fixture
def client():
    return TestClient(app, headers=AUTH_HEADERS)


def _create_account(client, code, metadata=None):
    payload = {
        "code": code,
        "name": f"Test {code}",
        "account_type": "asset",
        "correlation_id": f"corr-setup-{code}",
    }
    if metadata is not None:
        payload["metadata"] = metadata
    resp = client.post("/tools/create_account", json=payload)
    assert resp.status_code == 200
    return resp.json()["account_id"]


def test_update_metadata_add_new_keys(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    acct_id = _create_account(client, "meta-add-1")
    resp = client.post("/tools/update_account_metadata", json={
        "account_id": acct_id,
        "metadata": {"institution": "Chase", "currency": "USD"},
        "correlation_id": "corr-meta-add-1",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "committed"
    assert body["account_id"] == acct_id
    assert body["metadata"] == {"institution": "Chase", "currency": "USD"}
    assert body["correlation_id"] == "corr-meta-add-1"
    assert body["output_hash"]


def test_update_metadata_merge_preserves_existing(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    acct_id = _create_account(client, "meta-merge-1", metadata={"a": "1", "b": "2"})
    resp = client.post("/tools/update_account_metadata", json={
        "account_id": acct_id,
        "metadata": {"c": "3"},
        "correlation_id": "corr-meta-merge-1",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["metadata"] == {"a": "1", "b": "2", "c": "3"}


def test_update_metadata_overwrite_existing_key(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    acct_id = _create_account(client, "meta-overwrite-1", metadata={"color": "red"})
    resp = client.post("/tools/update_account_metadata", json={
        "account_id": acct_id,
        "metadata": {"color": "blue"},
        "correlation_id": "corr-meta-overwrite-1",
    })
    assert resp.status_code == 200
    assert resp.json()["metadata"] == {"color": "blue"}


def test_update_metadata_null_removes_key(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    acct_id = _create_account(client, "meta-null-1", metadata={"keep": "yes", "remove": "this"})
    resp = client.post("/tools/update_account_metadata", json={
        "account_id": acct_id,
        "metadata": {"remove": None},
        "correlation_id": "corr-meta-null-1",
    })
    assert resp.status_code == 200
    assert resp.json()["metadata"] == {"keep": "yes"}


def test_update_metadata_full_roundtrip(db_available, client):
    """Create account with metadata via create_account, then update, verify merged result."""
    if not db_available:
        pytest.skip("database unavailable")

    acct_id = _create_account(client, "meta-roundtrip-1", metadata={"institution": "Chase"})

    # Add keys
    resp1 = client.post("/tools/update_account_metadata", json={
        "account_id": acct_id,
        "metadata": {"type": "checking", "branch": "main"},
        "correlation_id": "corr-meta-rt-1",
    })
    assert resp1.status_code == 200
    assert resp1.json()["metadata"] == {"institution": "Chase", "type": "checking", "branch": "main"}

    # Overwrite + remove
    resp2 = client.post("/tools/update_account_metadata", json={
        "account_id": acct_id,
        "metadata": {"branch": None, "type": "savings"},
        "correlation_id": "corr-meta-rt-2",
    })
    assert resp2.status_code == 200
    assert resp2.json()["metadata"] == {"institution": "Chase", "type": "savings"}


def test_update_metadata_nonexistent_account(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    resp = client.post("/tools/update_account_metadata", json={
        "account_id": "nonexistent-acct-id",
        "metadata": {"key": "value"},
        "correlation_id": "corr-meta-404",
    })
    assert resp.status_code == 400
    assert "does not exist" in resp.json()["detail"]["message"]


def test_update_metadata_missing_required_fields(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    # Missing account_id
    resp = client.post("/tools/update_account_metadata", json={
        "metadata": {"key": "value"},
        "correlation_id": "corr-meta-miss-1",
    })
    assert resp.status_code == 422

    # Missing metadata
    resp = client.post("/tools/update_account_metadata", json={
        "account_id": "some-id",
        "correlation_id": "corr-meta-miss-2",
    })
    assert resp.status_code == 422


def test_update_metadata_not_an_object(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    resp = client.post("/tools/update_account_metadata", json={
        "account_id": "some-id",
        "metadata": "not-an-object",
        "correlation_id": "corr-meta-notobj",
    })
    assert resp.status_code == 422


def test_update_metadata_auth_required(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    no_auth_client = TestClient(app)
    resp = no_auth_client.post("/tools/update_account_metadata", json={
        "account_id": "some-id",
        "metadata": {"key": "value"},
        "correlation_id": "corr-meta-noauth",
    })
    assert resp.status_code == 401


def test_update_metadata_reader_token_forbidden(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    reader_client = TestClient(app, headers=READ_ONLY_AUTH_HEADERS)
    resp = reader_client.post("/tools/update_account_metadata", json={
        "account_id": "some-id",
        "metadata": {"key": "value"},
        "correlation_id": "corr-meta-reader",
    })
    assert resp.status_code == 403


def test_update_metadata_missing_correlation_id(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    resp = client.post("/tools/update_account_metadata", json={
        "account_id": "some-id",
        "metadata": {"key": "value"},
    })
    assert resp.status_code == 422


def test_update_metadata_event_logged(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    acct_id = _create_account(client, "meta-evtlog-1")
    resp = client.post("/tools/update_account_metadata", json={
        "account_id": acct_id,
        "metadata": {"logged": "yes"},
        "correlation_id": "corr-meta-evtlog",
    })
    assert resp.status_code == 200
    body = resp.json()

    with transaction() as conn:
        row = conn.execute(
            "SELECT * FROM event_log WHERE tool_name='update_account_metadata' AND correlation_id=?",
            ("corr-meta-evtlog",),
        ).fetchone()

    assert row is not None
    assert row["output_hash"] == body["output_hash"]
    assert row["input_hash"]
    assert row["status"] == "ok"
