import pytest

from capital_os.config import get_settings
from capital_os.db.session import transaction
from capital_os.domain.accounts.service import create_account_entry, update_account_profile
from capital_os.observability.hashing import payload_hash


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _create_account(code: str) -> str:
    return create_account_entry(
        {
            "code": code,
            "name": f"Replay {code}",
            "account_type": "asset",
            "correlation_id": f"corr-create-{code}",
        }
    )["account_id"]


def test_update_account_profile_replay_returns_canonical_hash(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    account_id = _create_account("prof-replay-1")
    first = update_account_profile(
        {
            "account_id": account_id,
            "display_name": "Replay Profile",
            "institution_name": "Replay CU",
            "institution_suffix": "RP-1",
            "source_system": "pytest",
            "external_id": "prof-replay-ext-1",
            "correlation_id": "corr-prof-replay-1a",
        }
    )
    replay = update_account_profile(
        {
            "account_id": account_id,
            "display_name": "ignored",
            "source_system": "pytest",
            "external_id": "prof-replay-ext-1",
            "correlation_id": "corr-prof-replay-1b",
        }
    )

    assert replay == first
    assert replay["output_hash"] == first["output_hash"]

    with transaction() as conn:
        event = conn.execute(
            """
            SELECT output_hash
            FROM event_log
            WHERE tool_name='update_account_profile' AND correlation_id=?
            """,
            ("corr-prof-replay-1b",),
        ).fetchone()
    assert event is not None
    assert event["output_hash"] == first["output_hash"]


def test_update_account_profile_output_hash_recomputes_from_response_payload(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    account_id = _create_account("prof-replay-2")
    result = update_account_profile(
        {
            "account_id": account_id,
            "display_name": "Hash Stable Name",
            "source_system": "pytest",
            "external_id": "prof-replay-ext-2",
            "correlation_id": "corr-prof-replay-2a",
        }
    )

    expected_hash = payload_hash(
        {
            "account_id": result["account_id"],
            "display_name": result["display_name"],
            "institution_name": result["institution_name"],
            "institution_suffix": result["institution_suffix"],
            "status": result["status"],
            "correlation_id": result["correlation_id"],
        }
    )
    assert result["output_hash"] == expected_hash
