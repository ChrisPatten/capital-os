"""Shared migration runner with applied-migration tracking.

Maintains a ``schema_migrations`` table inside the target SQLite database so
that ``apply_pending_migrations`` is safe to call repeatedly — already-applied
migrations are skipped, new ones are applied in order and recorded atomically.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


_BOOTSTRAP_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename   TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def _open_conn(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def discover_forward_migrations(migrations_dir: Path) -> list[Path]:
    """Return all forward migration files sorted by filename."""
    return sorted(
        p
        for p in migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.sql")
        if not p.name.endswith(".rollback.sql")
    )


def apply_pending_migrations(
    db_path: Path,
    migrations_dir: Path,
) -> tuple[list[str], list[str]]:
    """Apply any not-yet-recorded forward migrations.

    Returns:
        (applied, skipped) — lists of filenames in each category.
    """
    conn = _open_conn(db_path)
    try:
        # executescript issues an implicit COMMIT before running, so this
        # safely bootstraps the tracking table even on a brand-new database.
        conn.executescript(_BOOTSTRAP_SQL)

        migrations = discover_forward_migrations(migrations_dir)
        if not migrations:
            raise RuntimeError(f"no forward migrations found in {migrations_dir}")

        applied: list[str] = []
        skipped: list[str] = []

        for migration in migrations:
            already = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE filename = ?",
                (migration.name,),
            ).fetchone()
            if already:
                skipped.append(migration.name)
                continue

            sql = migration.read_text(encoding="utf-8")
            # executescript commits any open transaction before execution.
            conn.executescript(sql)

            # Record the migration as applied immediately after it succeeds.
            # If this insert fails the migration will be retried on next run.
            conn.execute(
                "INSERT INTO schema_migrations (filename) VALUES (?)",
                (migration.name,),
            )
            conn.commit()
            applied.append(migration.name)

        return applied, skipped
    finally:
        conn.close()
