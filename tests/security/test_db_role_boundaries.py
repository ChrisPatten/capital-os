import pytest
import sqlite3

from capital_os.db.session import read_only_connection, transaction


def test_read_only_connection_cannot_write_ledger_tables(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    with transaction() as conn:
        conn.execute(
            "INSERT INTO accounts (account_id, code, name, account_type) VALUES (?, ?, ?, ?)",
            ("seed", "seed", "Seed", "asset"),
        )

    with pytest.raises(sqlite3.OperationalError):
        with read_only_connection() as conn:
            conn.execute(
                "INSERT INTO accounts (account_id, code, name, account_type) VALUES (?, ?, ?, ?)",
                ("ro", "ro", "RO", "asset"),
            )


def test_read_only_connection_cannot_write_approval_tables(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    with pytest.raises(sqlite3.OperationalError):
        with read_only_connection() as conn:
            conn.execute(
                """
                INSERT INTO approval_proposals (
                  proposal_id, tool_name, source_system, external_id,
                  correlation_id, input_hash, request_payload, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "ro-proposal",
                    "record_transaction_bundle",
                    "pytest",
                    "ro-ext",
                    "corr-ro",
                    "hash-ro",
                    "{}",
                    "proposed",
                ),
            )
