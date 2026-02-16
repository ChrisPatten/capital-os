from __future__ import annotations

from pathlib import Path

from capital_os.config import get_settings
from capital_os.db.session import run_sql_file


_MIGRATION_FILES = (
    "0001_ledger_core.sql",
    "0002_security_and_append_only.sql",
    "0003_approval_gates.sql",
    "0004_read_query_indexes.sql",
    "0005_entity_dimension.sql",
    "0006_periods_policies.sql",
    "0007_query_surface_indexes.sql",
    "0008_api_security_runtime_controls.sql",
)


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

    migrations_dir = Path(__file__).resolve().parents[3] / "migrations"
    for migration_name in _MIGRATION_FILES:
        run_sql_file(migrations_dir / migration_name)
