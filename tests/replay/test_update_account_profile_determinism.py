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


def _setup_account(code: str) -> str:
    return create_account_entry(
        {
            "code": code,
            "name": f"Det {code}",
            "account_type": "asset",
            "correlation_id": f"corr-create-{code}",
        }
    )["account_id"]


def test_update_account_profile_output_hash_matches_deterministic_payload_hash(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    account_id = _setup_account("det-prof-1")
    payload = {
        "account_id": account_id,
        "display_name": "Deterministic Name",
        "institution_name": "Det CU",
        "institution_suffix": "D-01",
        "source_system": "pytest",
        "external_id": "det-prof-ext-1",
        "correlation_id": "corr-det-prof-1",
    }
    result = update_account_profile(payload)

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


def test_update_account_profile_duplicate_idempotency_key_replays_same_output_hash(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    account_id = _setup_account("det-prof-2")
    payload = {
        "account_id": account_id,
        "display_name": "Stable Replay",
        "source_system": "pytest",
        "external_id": "det-prof-ext-2",
        "correlation_id": "corr-det-prof-2a",
    }
    first = update_account_profile(payload)
    second = update_account_profile(
        {
            **payload,
            "display_name": "ignored-due-to-idempotency",
            "correlation_id": "corr-det-prof-2b",
        }
    )

    assert second == first

    with transaction() as conn:
        replay_event = conn.execute(
            """
            SELECT output_hash
            FROM event_log
            WHERE tool_name='update_account_profile' AND correlation_id=?
            """,
            ("corr-det-prof-2b",),
        ).fetchone()

    assert replay_event is not None
    assert replay_event["output_hash"] == first["output_hash"]
