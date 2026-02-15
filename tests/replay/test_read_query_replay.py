import pytest

from capital_os.domain.ledger.repository import create_account
from capital_os.domain.ledger.service import record_balance_snapshot, record_transaction_bundle
from capital_os.tools.get_account_balances import handle as get_account_balances_tool
from capital_os.tools.get_account_tree import handle as get_account_tree_tool
from capital_os.tools.list_accounts import handle as list_accounts_tool
from capital_os.db.session import transaction


def _seed_read_state() -> dict[str, str]:
    with transaction() as conn:
        root = create_account(conn, {"code": "1000", "name": "Assets", "account_type": "asset"})
        cash = create_account(
            conn,
            {"code": "1100", "name": "Cash", "account_type": "asset", "parent_account_id": root},
        )
        equity = create_account(conn, {"code": "3000", "name": "Equity", "account_type": "equity"})

    record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "read-replay-1",
            "date": "2026-01-05T00:00:00Z",
            "description": "read replay",
            "postings": [
                {"account_id": cash, "amount": "100.0000", "currency": "USD"},
                {"account_id": equity, "amount": "-100.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-read-replay-tx",
        }
    )
    record_balance_snapshot(
        {
            "source_system": "pytest",
            "account_id": cash,
            "snapshot_date": "2026-01-06",
            "balance": "95.0000",
            "currency": "USD",
            "correlation_id": "corr-read-replay-snap",
        }
    )
    return {"root": root}


def test_read_query_output_hash_reproducible_for_same_state_and_input(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    ids = _seed_read_state()

    list_payload = {"limit": 10, "correlation_id": "corr-read-replay-list"}
    list_first = list_accounts_tool(list_payload).model_dump(mode="json")
    list_second = list_accounts_tool(list_payload).model_dump(mode="json")
    assert list_first == list_second
    assert list_first["output_hash"] == list_second["output_hash"]

    tree_payload = {"root_account_id": ids["root"], "correlation_id": "corr-read-replay-tree"}
    tree_first = get_account_tree_tool(tree_payload).model_dump(mode="json")
    tree_second = get_account_tree_tool(tree_payload).model_dump(mode="json")
    assert tree_first == tree_second
    assert tree_first["output_hash"] == tree_second["output_hash"]

    balances_payload = {
        "as_of_date": "2026-01-10",
        "source_policy": "best_available",
        "correlation_id": "corr-read-replay-bal",
    }
    bal_first = get_account_balances_tool(balances_payload).model_dump(mode="json")
    bal_second = get_account_balances_tool(balances_payload).model_dump(mode="json")
    assert bal_first == bal_second
    assert bal_first["output_hash"] == bal_second["output_hash"]
