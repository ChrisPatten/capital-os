import pytest

from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account, list_accounts_subtree


def test_account_subtree_and_cycle_rejection(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    with transaction() as conn:
        root = create_account(conn, {"code": "1000", "name": "Assets", "account_type": "asset"})
        child = create_account(
            conn,
            {
                "code": "1100",
                "name": "Checking",
                "account_type": "asset",
                "parent_account_id": root,
            },
        )

    with transaction() as conn:
        rows = list_accounts_subtree(conn, root)
        assert [r["code"] for r in rows] == ["1000", "1100"]

    with pytest.raises(Exception):
        with transaction() as conn:
            conn.execute("UPDATE accounts SET parent_account_id=? WHERE account_id=?", (child, root))
