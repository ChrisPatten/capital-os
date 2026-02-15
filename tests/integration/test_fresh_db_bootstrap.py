from __future__ import annotations

from pathlib import Path
import sqlite3

from capital_os.config import get_settings
from capital_os.db.testing import reset_test_database


def test_reset_bootstrap_succeeds_on_fresh_sqlite_file(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "fresh-bootstrap.db"
    monkeypatch.setenv("CAPITAL_OS_DB_URL", f"sqlite:///{db_path}")
    get_settings.cache_clear()

    try:
        reset_test_database()

        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='ledger_transactions'"
            ).fetchone()
            assert row is not None
        finally:
            conn.close()
    finally:
        get_settings.cache_clear()
