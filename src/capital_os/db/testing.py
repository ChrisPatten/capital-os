from __future__ import annotations

from pathlib import Path

from capital_os.config import get_settings
from capital_os.db.migrations import apply_pending_migrations


_MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"


def _sqlite_path_from_db_url(db_url: str) -> Path:
    if not db_url.startswith("sqlite:///"):
        raise ValueError("CAPITAL_OS_DB_URL must use sqlite:/// URL format")
    raw_path = db_url.removeprefix("sqlite:///")
    if not raw_path:
        raise ValueError("CAPITAL_OS_DB_URL sqlite path cannot be empty")
    return Path(raw_path)


def reset_test_database() -> None:
    db_path = _sqlite_path_from_db_url(get_settings().db_url)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove the SQLite database and WAL sidecars so test bootstrap is deterministic.
    for suffix in ("", "-wal", "-shm"):
        Path(f"{db_path}{suffix}").unlink(missing_ok=True)

    # Deleting the DB also removes schema_migrations, so all migrations are
    # treated as pending and applied fresh — correct for test isolation.
    apply_pending_migrations(db_path, _MIGRATIONS_DIR)
