from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from capital_os.config import get_settings
from capital_os.db.session import run_sql_file, transaction


@pytest.fixture(scope="session")
def db_available() -> bool:
    try:
        db_url = get_settings().db_url
        if not db_url.startswith("sqlite:///"):
            return False
        db_path = db_url.removeprefix("sqlite:///")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def migrated_db(db_available: bool):
    if not db_available:
        yield
        return

    # Reset any pre-existing local schema so non-idempotent ALTER migrations can re-apply cleanly.
    run_sql_file(Path("migrations/0006_periods_policies.rollback.sql"))
    run_sql_file(Path("migrations/0005_entity_dimension.rollback.sql"))
    run_sql_file(Path("migrations/0004_read_query_indexes.rollback.sql"))
    run_sql_file(Path("migrations/0003_approval_gates.rollback.sql"))
    run_sql_file(Path("migrations/0002_security_and_append_only.rollback.sql"))
    run_sql_file(Path("migrations/0001_ledger_core.rollback.sql"))

    run_sql_file(Path("migrations/0001_ledger_core.sql"))
    run_sql_file(Path("migrations/0002_security_and_append_only.sql"))
    run_sql_file(Path("migrations/0003_approval_gates.sql"))
    run_sql_file(Path("migrations/0004_read_query_indexes.sql"))
    run_sql_file(Path("migrations/0005_entity_dimension.sql"))
    run_sql_file(Path("migrations/0006_periods_policies.sql"))
    yield


@pytest.fixture(autouse=True)
def clean_db(db_available: bool):
    if not db_available:
        yield
        return

    run_sql_file(Path("migrations/0006_periods_policies.rollback.sql"))
    run_sql_file(Path("migrations/0005_entity_dimension.rollback.sql"))
    run_sql_file(Path("migrations/0004_read_query_indexes.rollback.sql"))
    run_sql_file(Path("migrations/0003_approval_gates.rollback.sql"))
    run_sql_file(Path("migrations/0002_security_and_append_only.rollback.sql"))
    run_sql_file(Path("migrations/0001_ledger_core.rollback.sql"))
    run_sql_file(Path("migrations/0001_ledger_core.sql"))
    run_sql_file(Path("migrations/0002_security_and_append_only.sql"))
    run_sql_file(Path("migrations/0003_approval_gates.sql"))
    run_sql_file(Path("migrations/0004_read_query_indexes.sql"))
    run_sql_file(Path("migrations/0005_entity_dimension.sql"))
    run_sql_file(Path("migrations/0006_periods_policies.sql"))
    yield
