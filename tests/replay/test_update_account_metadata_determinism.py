import pytest

from capital_os.config import get_settings
from capital_os.db.session import transaction
from capital_os.domain.accounts.service import create_account_entry, update_account_metadata
from capital_os.observability.hashing import payload_hash


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _setup_account(code, metadata=None):
    payload = {
        "code": code,
        "name": f"Det {code}",
        "account_type": "asset",
        "correlation_id": f"corr-setup-det-{code}",
    }
    if metadata is not None:
        payload["metadata"] = metadata
    return create_account_entry(payload)["account_id"]


def test_update_account_metadata_output_hash_deterministic(db_available):
    """Identical inputs on identical state produce identical output_hash."""
    if not db_available:
        pytest.skip("database unavailable")

    acct_id = _setup_account("det-meta-1", metadata={"existing": "data"})
    payload = {
        "account_id": acct_id,
        "metadata": {"new_key": "new_value"},
        "correlation_id": "corr-det-meta-1",
    }

    result = update_account_metadata(payload)
    assert result["status"] == "committed"
    assert result["output_hash"]

    # Verify the output_hash matches recomputation from response fields
    response_for_hash = {
        "account_id": result["account_id"],
        "metadata": result["metadata"],
        "status": result["status"],
        "correlation_id": result["correlation_id"],
    }
    expected_hash = payload_hash(response_for_hash)
    assert result["output_hash"] == expected_hash


def test_update_account_metadata_event_log_hashes_match(db_available):
    """Event log input_hash and output_hash match the tool's computation."""
    if not db_available:
        pytest.skip("database unavailable")

    acct_id = _setup_account("det-meta-2")
    payload = {
        "account_id": acct_id,
        "metadata": {"key": "value"},
        "correlation_id": "corr-det-meta-2",
    }

    expected_input_hash = payload_hash(payload)
    result = update_account_metadata(payload)

    with transaction() as conn:
        row = conn.execute(
            "SELECT input_hash, output_hash FROM event_log WHERE tool_name='update_account_metadata' AND correlation_id=?",
            ("corr-det-meta-2",),
        ).fetchone()

    assert row is not None
    assert row["input_hash"] == expected_input_hash
    assert row["output_hash"] == result["output_hash"]
