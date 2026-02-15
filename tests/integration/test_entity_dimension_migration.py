from __future__ import annotations

import pytest

from capital_os.config import get_settings
from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.domain.ledger.service import (
    create_or_update_obligation,
    record_balance_snapshot,
    record_transaction_bundle,
)


def test_default_entity_seeded_and_applied_to_writes(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    with transaction() as conn:
        default_entity = conn.execute(
            "SELECT entity_id, code, name FROM entities WHERE entity_id='entity-default'"
        ).fetchone()
        assert default_entity is not None
        assert default_entity["code"] == "DEFAULT"
        assert default_entity["name"] == "Default Entity"

        cash = create_account(conn, {"code": "1000", "name": "Cash", "account_type": "asset"})
        equity = create_account(conn, {"code": "3000", "name": "Equity", "account_type": "equity"})

    tx_result = record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "entity-default-tx",
            "date": "2026-02-15T00:00:00Z",
            "description": "default entity opening",
            "postings": [
                {"account_id": cash, "amount": "125.0000", "currency": "USD"},
                {"account_id": equity, "amount": "-125.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-entity-default-tx",
        }
    )
    record_balance_snapshot(
        {
            "source_system": "pytest",
            "account_id": cash,
            "snapshot_date": "2026-02-15",
            "balance": "125.0000",
            "currency": "USD",
            "correlation_id": "corr-entity-default-snap",
        }
    )
    create_or_update_obligation(
        {
            "source_system": "pytest",
            "name": "Rent",
            "account_id": cash,
            "cadence": "monthly",
            "expected_amount": "10.0000",
            "next_due_date": "2026-03-01",
            "correlation_id": "corr-entity-default-obl",
        }
    )

    with transaction() as conn:
        account_entity = conn.execute("SELECT entity_id FROM accounts WHERE account_id=?", (cash,)).fetchone()
        tx_entity = conn.execute(
            "SELECT entity_id FROM ledger_transactions WHERE transaction_id=?",
            (tx_result["transaction_id"],),
        ).fetchone()
        snapshot_entity = conn.execute(
            "SELECT entity_id FROM balance_snapshots WHERE account_id=?",
            (cash,),
        ).fetchone()
        obligation_entity = conn.execute(
            "SELECT entity_id FROM obligations WHERE account_id=?",
            (cash,),
        ).fetchone()

    assert account_entity["entity_id"] == "entity-default"
    assert tx_entity["entity_id"] == "entity-default"
    assert snapshot_entity["entity_id"] == "entity-default"
    assert obligation_entity["entity_id"] == "entity-default"


def test_custom_entity_id_propagates_to_records(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO entities (entity_id, code, name, metadata)
            VALUES (?, ?, ?, '{}')
            """,
            ("entity-holding-co", "HOLDCO", "Holding Co"),
        )
        cash = create_account(
            conn,
            {
                "code": "1100",
                "name": "Holding Cash",
                "account_type": "asset",
                "entity_id": "entity-holding-co",
            },
        )
        equity = create_account(
            conn,
            {
                "code": "3100",
                "name": "Holding Equity",
                "account_type": "equity",
                "entity_id": "entity-holding-co",
            },
        )

    tx_result = record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "entity-custom-tx",
            "date": "2026-02-16T00:00:00Z",
            "description": "custom entity opening",
            "entity_id": "entity-holding-co",
            "postings": [
                {"account_id": cash, "amount": "210.0000", "currency": "USD"},
                {"account_id": equity, "amount": "-210.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-entity-custom-tx",
        }
    )
    record_balance_snapshot(
        {
            "source_system": "pytest",
            "account_id": cash,
            "snapshot_date": "2026-02-16",
            "balance": "210.0000",
            "currency": "USD",
            "entity_id": "entity-holding-co",
            "correlation_id": "corr-entity-custom-snap",
        }
    )
    create_or_update_obligation(
        {
            "source_system": "pytest",
            "name": "Payroll",
            "account_id": cash,
            "cadence": "monthly",
            "expected_amount": "25.0000",
            "next_due_date": "2026-03-10",
            "entity_id": "entity-holding-co",
            "correlation_id": "corr-entity-custom-obl",
        }
    )

    with transaction() as conn:
        tx_entity = conn.execute(
            "SELECT entity_id FROM ledger_transactions WHERE transaction_id=?",
            (tx_result["transaction_id"],),
        ).fetchone()
        snapshot_entity = conn.execute(
            "SELECT entity_id FROM balance_snapshots WHERE account_id=?",
            (cash,),
        ).fetchone()
        obligation_entity = conn.execute(
            "SELECT entity_id FROM obligations WHERE account_id=?",
            (cash,),
        ).fetchone()

    assert tx_entity["entity_id"] == "entity-holding-co"
    assert snapshot_entity["entity_id"] == "entity-holding-co"
    assert obligation_entity["entity_id"] == "entity-holding-co"


def test_approval_proposal_entity_id_is_immutable(db_available, monkeypatch):
    if not db_available:
        pytest.skip("database unavailable")

    monkeypatch.setenv("CAPITAL_OS_APPROVAL_THRESHOLD_AMOUNT", "100.0000")
    get_settings.cache_clear()

    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO entities (entity_id, code, name, metadata)
            VALUES (?, ?, ?, '{}')
            """,
            ("entity-family-office", "FAMOFF", "Family Office"),
        )
        debit = create_account(
            conn,
            {
                "code": "1200",
                "name": "FO Cash",
                "account_type": "asset",
                "entity_id": "entity-family-office",
            },
        )
        credit = create_account(
            conn,
            {
                "code": "3200",
                "name": "FO Equity",
                "account_type": "equity",
                "entity_id": "entity-family-office",
            },
        )

    result = record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "entity-proposal-1",
            "date": "2026-02-17T00:00:00Z",
            "description": "proposal for immutable entity",
            "entity_id": "entity-family-office",
            "postings": [
                {"account_id": debit, "amount": "250.0000", "currency": "USD"},
                {"account_id": credit, "amount": "-250.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-entity-proposal-1",
        }
    )
    assert result["status"] == "proposed"

    with transaction() as conn:
        proposal = conn.execute(
            "SELECT proposal_id, entity_id FROM approval_proposals WHERE external_id='entity-proposal-1'"
        ).fetchone()
        assert proposal["entity_id"] == "entity-family-office"
        with pytest.raises(Exception):
            conn.execute(
                "UPDATE approval_proposals SET entity_id=? WHERE proposal_id=?",
                ("entity-default", proposal["proposal_id"]),
            )

    get_settings.cache_clear()
