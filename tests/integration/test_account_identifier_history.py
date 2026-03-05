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


def _profile_headers(correlation_id: str) -> dict[str, str]:
    return {**AUTH_HEADERS, "x-correlation-id": correlation_id}


def test_identifier_history_inserted_on_first_profile_update(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    account_id = _create_account(client, "hist-1000")
    response = client.post(
        "/tools/update_account_profile",
        headers=_profile_headers("corr-hist-1"),
        json={
            "account_id": account_id,
            "display_name": "New Name 1",
            "institution_suffix": "SFX-001",
            "source_system": "pytest",
            "external_id": "hist-ext-1",
            "correlation_id": "corr-hist-1",
        },
    )
    assert response.status_code == 200

    with transaction() as conn:
        rows = conn.execute(
            """
            SELECT source_system, external_id, institution_suffix, valid_from, valid_to
            FROM account_identifier_history
            WHERE account_id = ? AND source_system = 'pytest'
            ORDER BY valid_from ASC
            """,
            (account_id,),
        ).fetchall()

    assert len(rows) == 1
    assert rows[0]["external_id"] == "hist-ext-1"
    assert rows[0]["institution_suffix"] == "SFX-001"
    assert rows[0]["valid_from"]
    assert rows[0]["valid_to"] is None


def test_identifier_history_rolls_over_on_identifier_change(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    account_id = _create_account(client, "hist-1001")
    first = client.post(
        "/tools/update_account_profile",
        headers=_profile_headers("corr-hist-2a"),
        json={
            "account_id": account_id,
            "display_name": "Name First",
            "institution_suffix": "SFX-A",
            "source_system": "pytest",
            "external_id": "hist-ext-a",
            "correlation_id": "corr-hist-2a",
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/tools/update_account_profile",
        headers=_profile_headers("corr-hist-2b"),
        json={
            "account_id": account_id,
            "display_name": "Name Second",
            "institution_suffix": "SFX-B",
            "source_system": "pytest",
            "external_id": "hist-ext-b",
            "correlation_id": "corr-hist-2b",
        },
    )
    assert second.status_code == 200

    with transaction() as conn:
        rows = conn.execute(
            """
            SELECT external_id, institution_suffix, valid_from, valid_to
            FROM account_identifier_history
            WHERE account_id = ? AND source_system = 'pytest'
            ORDER BY valid_from ASC
            """,
            (account_id,),
        ).fetchall()
        active = conn.execute(
            """
            SELECT external_id, institution_suffix
            FROM account_identifier_history
            WHERE account_id = ? AND source_system = 'pytest' AND valid_to IS NULL
            """,
            (account_id,),
        ).fetchone()

    assert len(rows) == 2
    assert rows[0]["external_id"] == "hist-ext-a"
    assert rows[0]["institution_suffix"] == "SFX-A"
    assert rows[0]["valid_to"] is not None
    assert rows[1]["external_id"] == "hist-ext-b"
    assert rows[1]["institution_suffix"] == "SFX-B"
    assert rows[1]["valid_to"] is None
    assert active is not None
    assert active["external_id"] == "hist-ext-b"


def test_identifier_history_not_duplicated_on_idempotent_replay(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    account_id = _create_account(client, "hist-1002")
    first = client.post(
        "/tools/update_account_profile",
        headers=_profile_headers("corr-hist-3a"),
        json={
            "account_id": account_id,
            "display_name": "Replay Name",
            "institution_suffix": "SFX-R",
            "source_system": "pytest",
            "external_id": "hist-ext-replay",
            "correlation_id": "corr-hist-3a",
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/tools/update_account_profile",
        headers=_profile_headers("corr-hist-3b"),
        json={
            "account_id": account_id,
            "display_name": "Should Not Change",
            "institution_suffix": "SFX-X",
            "source_system": "pytest",
            "external_id": "hist-ext-replay",
            "correlation_id": "corr-hist-3b",
        },
    )
    assert second.status_code == 200
    assert second.json() == first.json()

    with transaction() as conn:
        count = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM account_identifier_history
            WHERE account_id = ? AND source_system = 'pytest'
            """,
            (account_id,),
        ).fetchone()["c"]

    assert count == 1


def test_identifier_history_update_rolls_back_if_event_log_insert_fails(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    account_id = _create_account(client, "hist-1003")
    with transaction() as conn:
        conn.execute(
            """
            CREATE TRIGGER fail_update_account_profile_event_log
            BEFORE INSERT ON event_log
            FOR EACH ROW
            WHEN NEW.tool_name='update_account_profile'
              AND NEW.correlation_id='corr-hist-rollback'
            BEGIN
              SELECT RAISE(ABORT, 'forced event log failure');
            END;
            """
        )

    failed = client.post(
        "/tools/update_account_profile",
        headers=_profile_headers("corr-hist-rollback"),
        json={
            "account_id": account_id,
            "display_name": "Should Roll Back",
            "institution_suffix": "SFX-ROLLBACK",
            "source_system": "pytest",
            "external_id": "hist-ext-rollback",
            "correlation_id": "corr-hist-rollback",
        },
    )
    assert failed.status_code >= 500

    with transaction() as conn:
        conn.execute("DROP TRIGGER IF EXISTS fail_update_account_profile_event_log")
        account = conn.execute(
            "SELECT name, metadata FROM accounts WHERE account_id=?",
            (account_id,),
        ).fetchone()
        history_rows = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM account_identifier_history
            WHERE account_id=? AND source_system='pytest'
            """,
            (account_id,),
        ).fetchone()["c"]
        proposals = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM approval_proposals
            WHERE tool_name='update_account_profile'
              AND source_system='pytest'
              AND external_id='hist-ext-rollback'
            """
        ).fetchone()["c"]

    assert account is not None
    assert account["name"] == "Account hist-1003"
    assert history_rows == 0
    assert proposals == 0


def test_identifier_history_table_blocks_destructive_mutations(db_available, client):
    if not db_available:
        pytest.skip("database unavailable")

    account_id = _create_account(client, "hist-1004")
    created = client.post(
        "/tools/update_account_profile",
        headers=_profile_headers("corr-hist-guard-1"),
        json={
            "account_id": account_id,
            "display_name": "Guard Name",
            "institution_suffix": "SFX-GUARD",
            "source_system": "pytest",
            "external_id": "hist-ext-guard",
            "correlation_id": "corr-hist-guard-1",
        },
    )
    assert created.status_code == 200

    with transaction() as conn:
        row = conn.execute(
            """
            SELECT history_id
            FROM account_identifier_history
            WHERE account_id=? AND source_system='pytest' AND valid_to IS NULL
            """,
            (account_id,),
        ).fetchone()
        assert row is not None
        history_id = row["history_id"]
        with pytest.raises(Exception):
            conn.execute(
                "DELETE FROM account_identifier_history WHERE history_id=?",
                (history_id,),
            )
