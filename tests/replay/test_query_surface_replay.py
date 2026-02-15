import pytest

from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.domain.ledger.service import create_or_update_obligation, record_transaction_bundle
from capital_os.tools.get_config import handle as get_config_tool
from capital_os.tools.get_transaction_by_external_id import handle as get_transaction_tool
from capital_os.tools.list_obligations import handle as list_obligations_tool
from capital_os.tools.list_transactions import handle as list_transactions_tool
from capital_os.tools.propose_config_change import handle as propose_config_change_tool


def _seed_state() -> None:
    with transaction() as conn:
        cash = create_account(conn, {"code": "1100", "name": "Cash", "account_type": "asset"})
        equity = create_account(conn, {"code": "3100", "name": "Equity", "account_type": "equity"})

    record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "replay-tx-1",
            "date": "2026-01-01T00:00:00Z",
            "description": "replay tx",
            "postings": [
                {"account_id": cash, "amount": "99.0000", "currency": "USD"},
                {"account_id": equity, "amount": "-99.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-replay-tx",
        }
    )

    create_or_update_obligation(
        {
            "source_system": "pytest",
            "name": "Replay Obligation",
            "account_id": cash,
            "cadence": "monthly",
            "expected_amount": "100.0000",
            "variability_flag": False,
            "next_due_date": "2026-02-01",
            "metadata": {},
            "correlation_id": "corr-replay-ob",
        }
    )

    propose_config_change_tool(
        {
            "source_system": "pytest",
            "external_id": "replay-config-1",
            "scope": "runtime_settings",
            "change_payload": {"balance_source_policy": "best_available"},
            "correlation_id": "corr-replay-config",
        }
    )


def test_query_surface_output_hash_reproducible_for_same_state_and_input(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    _seed_state()

    tx_payload = {"limit": 10, "correlation_id": "corr-replay-list-tx"}
    tx_first = list_transactions_tool(tx_payload).model_dump(mode="json")
    tx_second = list_transactions_tool(tx_payload).model_dump(mode="json")
    assert tx_first == tx_second
    assert tx_first["output_hash"] == tx_second["output_hash"]

    get_payload = {
        "source_system": "pytest",
        "external_id": "replay-tx-1",
        "correlation_id": "corr-replay-get-tx",
    }
    get_first = get_transaction_tool(get_payload).model_dump(mode="json")
    get_second = get_transaction_tool(get_payload).model_dump(mode="json")
    assert get_first == get_second
    assert get_first["output_hash"] == get_second["output_hash"]

    ob_payload = {"limit": 10, "active_only": True, "correlation_id": "corr-replay-ob-list"}
    ob_first = list_obligations_tool(ob_payload).model_dump(mode="json")
    ob_second = list_obligations_tool(ob_payload).model_dump(mode="json")
    assert ob_first == ob_second
    assert ob_first["output_hash"] == ob_second["output_hash"]

    cfg_payload = {"correlation_id": "corr-replay-get-config"}
    cfg_first = get_config_tool(cfg_payload).model_dump(mode="json")
    cfg_second = get_config_tool(cfg_payload).model_dump(mode="json")
    assert cfg_first == cfg_second
    assert cfg_first["output_hash"] == cfg_second["output_hash"]
