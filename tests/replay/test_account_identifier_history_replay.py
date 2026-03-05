import pytest

from capital_os.config import get_settings
from capital_os.db.session import transaction
from capital_os.domain.accounts.service import create_account_entry, update_account_profile


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _create_account(code: str) -> str:
    return create_account_entry(
        {
            "code": code,
            "name": f"Hist {code}",
            "account_type": "asset",
            "correlation_id": f"corr-create-{code}",
        }
    )["account_id"]


def test_identifier_history_replay_keeps_hash_and_single_history_row(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    account_id = _create_account("hist-det-1")
    first = update_account_profile(
        {
            "account_id": account_id,
            "display_name": "Replay Deterministic",
            "institution_suffix": "R-001",
            "source_system": "pytest",
            "external_id": "hist-det-ext-1",
            "correlation_id": "corr-hist-det-1a",
        }
    )
    second = update_account_profile(
        {
            "account_id": account_id,
            "display_name": "ignored",
            "institution_suffix": "ignored",
            "source_system": "pytest",
            "external_id": "hist-det-ext-1",
            "correlation_id": "corr-hist-det-1b",
        }
    )

    assert first == second

    with transaction() as conn:
        row_count = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM account_identifier_history
            WHERE account_id=? AND source_system='pytest'
            """,
            (account_id,),
        ).fetchone()["c"]

    assert row_count == 1


def test_identifier_history_transition_on_external_id_change(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    account_id = _create_account("hist-det-2")
    update_account_profile(
        {
            "account_id": account_id,
            "display_name": "Start",
            "institution_suffix": "S-001",
            "source_system": "pytest",
            "external_id": "hist-det-ext-a",
            "correlation_id": "corr-hist-det-2a",
        }
    )
    update_account_profile(
        {
            "account_id": account_id,
            "display_name": "Changed",
            "institution_suffix": "S-001",
            "source_system": "pytest",
            "external_id": "hist-det-ext-b",
            "correlation_id": "corr-hist-det-2b",
        }
    )

    with transaction() as conn:
        rows = conn.execute(
            """
            SELECT external_id, institution_suffix, valid_to
            FROM account_identifier_history
            WHERE account_id=? AND source_system='pytest'
            ORDER BY valid_from ASC
            """,
            (account_id,),
        ).fetchall()

    assert len(rows) == 2
    assert rows[0]["external_id"] == "hist-det-ext-a"
    assert rows[0]["valid_to"] is not None
    assert rows[1]["external_id"] == "hist-det-ext-b"
    assert rows[1]["institution_suffix"] == "S-001"
    assert rows[1]["valid_to"] is None
