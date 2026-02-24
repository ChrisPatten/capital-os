from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from urllib.parse import quote

from capital_os.config import get_settings


def _sqlite_path_from_url(db_url: str) -> str:
    if not db_url.startswith("sqlite:///"):
        raise ValueError("CAPITAL_OS_DB_URL must use sqlite:/// URL format")
    path = db_url.removeprefix("sqlite:///")
    if not path:
        raise ValueError("CAPITAL_OS_DB_URL sqlite path cannot be empty")
    return path


def _connect(read_only: bool = False) -> sqlite3.Connection:
    db_path = _sqlite_path_from_url(get_settings().db_url)
    path = Path(db_path)
    if not read_only:
        path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    if read_only:
        # Use query_only pragma instead of mode=ro URI to avoid WAL shm-file
        # creation failures on freshly-reset databases.  Any write attempt
        # still raises sqlite3.OperationalError ("attempt to write a readonly
        # database"), preserving the security boundary tested in
        # tests/security/test_db_role_boundaries.py.
        conn.execute("PRAGMA query_only = ON")
    return conn


def probe_ready_noncreating() -> None:
    """Verify the configured SQLite DB is reachable without creating files.

    Used by health/readiness endpoints so a misconfigured path does not create
    an empty SQLite database as a side effect.
    """
    db_path = _sqlite_path_from_url(get_settings().db_url)
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"Database file not found: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"Database path is not a file: {path}")

    # Use SQLite URI read-only mode to avoid implicit file creation.
    uri = f"file:{quote(str(path.resolve()))}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        conn.execute("SELECT 1 AS ok").fetchone()
    finally:
        conn.close()


@contextmanager
def transaction():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def read_only_connection():
    conn = _connect(read_only=True)
    try:
        yield conn
    finally:
        conn.close()


def run_sql_file(path: str | Path) -> None:
    sql = Path(path).read_text(encoding="utf-8")
    with transaction() as conn:
        conn.executescript(sql)
