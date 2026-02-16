from __future__ import annotations

import json

import pytest

from capital_os.db.coa_importer import CoaImportError, import_coa_payload
from capital_os.db.session import transaction


def test_coa_import_creates_accounts(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    payload = {
        "version": 1,
        "metadata": {"currency": "USD"},
        "accounts": [
            {
                "account_id": "ast_cash",
                "name": "Assets:Cash",
                "type": "ASSET",
                "description": "Cash account",
                "tags": ["cash"],
            },
            {
                "account_id": "eq_opening_balances",
                "name": "Equity:OpeningBalances",
                "type": "EQUITY",
                "parent_id": None,
            },
        ],
    }

    summary = import_coa_payload(payload)
    assert summary.created == 2
    assert summary.updated == 0
    assert summary.unchanged == 0

    with transaction() as conn:
        rows = conn.execute(
            "SELECT account_id, code, account_type, metadata FROM accounts ORDER BY account_id"
        ).fetchall()
    assert [row["account_id"] for row in rows] == ["ast_cash", "eq_opening_balances"]
    assert [row["code"] for row in rows] == ["ast_cash", "eq_opening_balances"]
    assert [row["account_type"] for row in rows] == ["asset", "equity"]
    metadata = json.loads(rows[0]["metadata"])
    assert metadata["description"] == "Cash account"
    assert metadata["currency"] == "USD"
    assert metadata["tags"] == ["cash"]
    assert metadata["is_active"] is True


def test_coa_import_upsert_updates_allowed_fields(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    first = {
        "version": 1,
        "accounts": [
            {
                "account_id": "ast_cash",
                "name": "Assets:Cash",
                "type": "ASSET",
                "description": "Old",
                "metadata": {"institution": "A"},
            }
        ],
    }
    second = {
        "version": 1,
        "import_policy": {
            "mode": "upsert",
            "allow_updates": {
                "name": True,
                "description": False,
                "metadata": False,
                "is_active": False,
                "parent_id": True,
            },
        },
        "accounts": [
            {
                "account_id": "ast_cash",
                "name": "Assets:Cash:Primary",
                "type": "ASSET",
                "description": "New",
                "metadata": {"institution": "B"},
                "is_active": False,
            }
        ],
    }

    import_coa_payload(first)
    summary = import_coa_payload(second)
    assert summary.created == 0
    assert summary.updated == 1
    assert summary.unchanged == 0

    with transaction() as conn:
        row = conn.execute("SELECT name, metadata FROM accounts WHERE account_id='ast_cash'").fetchone()
    assert row["name"] == "Assets:Cash:Primary"
    metadata = json.loads(row["metadata"])
    assert metadata["description"] == "Old"
    assert metadata["institution"] == "A"
    assert metadata["is_active"] is True


def test_coa_import_rejects_invalid_type():
    payload = {
        "version": 1,
        "accounts": [{"account_id": "x", "name": "X", "type": "INVALID"}],
    }
    with pytest.raises(CoaImportError, match="type must be one of"):
        import_coa_payload(payload, dry_run=True)


def test_coa_import_rejects_parent_cycle():
    payload = {
        "version": 1,
        "accounts": [
            {"account_id": "a", "name": "A", "type": "ASSET", "parent_id": "b"},
            {"account_id": "b", "name": "B", "type": "ASSET", "parent_id": "a"},
        ],
    }
    with pytest.raises(CoaImportError, match="acyclic"):
        import_coa_payload(payload, dry_run=True)


def test_coa_import_rejects_duplicate_account_id():
    payload = {
        "version": 1,
        "accounts": [
            {"account_id": "dup", "name": "A", "type": "ASSET"},
            {"account_id": "dup", "name": "B", "type": "ASSET"},
        ],
    }
    with pytest.raises(CoaImportError, match="duplicate account_id"):
        import_coa_payload(payload, dry_run=True)


def test_coa_import_rejects_missing_parent_reference():
    payload = {
        "version": 1,
        "accounts": [
            {"account_id": "a", "name": "A", "type": "ASSET", "parent_id": "missing"},
        ],
    }
    with pytest.raises(CoaImportError, match="unknown parent_id"):
        import_coa_payload(payload, dry_run=True)
