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
