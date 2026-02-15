#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def load_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def migration_sets(migrations_dir: Path) -> tuple[list[Path], list[Path]]:
    forward = sorted(
        p
        for p in migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.sql")
        if not p.name.endswith(".rollback.sql")
    )
    if not forward:
        raise RuntimeError(f"no forward migrations found in {migrations_dir}")

    rollback: list[Path] = []
    for migration in forward:
        rollback_path = migration.with_name(f"{migration.stem}.rollback.sql")
        if not rollback_path.exists():
            raise RuntimeError(f"missing rollback migration for {migration.name}: {rollback_path.name}")
        rollback.append(rollback_path)

    return forward, rollback


def run_scripts(conn: sqlite3.Connection, scripts: list[Path], phase: str) -> None:
    for script in scripts:
        print(f"[{phase}] {script}")
        conn.executescript(load_sql(script))


def user_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [row[0] for row in rows]


def remove_sqlite_files(db_path: Path) -> None:
    for candidate in (db_path, Path(f"{db_path}-shm"), Path(f"{db_path}-wal")):
        if candidate.exists():
            candidate.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify migrations apply, rollback, and re-apply")
    parser.add_argument("--db-path", default="data/migration-cycle.db", help="SQLite path for migration cycle checks")
    parser.add_argument("--migrations-dir", default="migrations", help="Directory containing migration SQL files")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    remove_sqlite_files(db_path)

    migrations_dir = Path(args.migrations_dir)
    forward, rollback = migration_sets(migrations_dir)

    conn = sqlite3.connect(db_path)
    try:
        print("Running migration apply -> rollback -> re-apply cycle")
        run_scripts(conn, forward, "apply")
        run_scripts(conn, list(reversed(rollback)), "rollback")

        remaining_tables = user_tables(conn)
        if remaining_tables:
            raise RuntimeError(f"rollback did not return to baseline; remaining tables: {remaining_tables}")

        run_scripts(conn, forward, "re-apply")
        print("Migration cycle check passed")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
