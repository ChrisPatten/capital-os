import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import app
from capital_os.config import get_settings
from capital_os.db.session import transaction
from capital_os.domain.accounts.service import create_account_entry
from capital_os.observability.hashing import payload_hash
from tests.support.auth import AUTH_HEADERS


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_create_account_output_hash_deterministic(db_available):
    """Identical inputs on a clean DB produce identical output_hash structure."""
    if not db_available:
        pytest.skip("database unavailable")

    payload = {
        "code": "det-1000",
        "name": "Deterministic Cash",
        "account_type": "asset",
        "correlation_id": "corr-det-1",
    }

    result = create_account_entry(payload)
    assert result["status"] == "committed"
    assert result["output_hash"]

    # Verify the output_hash matches recomputation from response fields
    response_for_hash = {
        "account_id": result["account_id"],
        "status": result["status"],
        "correlation_id": result["correlation_id"],
    }
    expected_hash = payload_hash(response_for_hash)
    assert result["output_hash"] == expected_hash


def test_create_account_event_log_hashes_match(db_available):
    """Event log input_hash and output_hash match the tool's computation."""
    if not db_available:
        pytest.skip("database unavailable")

    payload = {
        "code": "hash-match-acct",
        "name": "Hash Match",
        "account_type": "liability",
        "correlation_id": "corr-hash-match",
    }

    expected_input_hash = payload_hash(payload)
    result = create_account_entry(payload)

    with transaction() as conn:
        row = conn.execute(
            "SELECT input_hash, output_hash FROM event_log WHERE tool_name='create_account' AND correlation_id=?",
            ("corr-hash-match",),
        ).fetchone()

    assert row is not None
    assert row["input_hash"] == expected_input_hash
    assert row["output_hash"] == result["output_hash"]
