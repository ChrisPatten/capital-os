from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from capital_os.config import get_settings
from capital_os.db.testing import reset_test_database


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

    reset_test_database()
    yield


@pytest.fixture(autouse=True)
def clean_db(db_available: bool):
    if not db_available:
        yield
        return

    reset_test_database()
    yield
