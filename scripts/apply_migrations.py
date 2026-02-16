#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from capital_os.db.session import run_sql_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply forward SQL migrations in order")
    parser.add_argument(
        "--migrations-dir",
        default=str(ROOT / "migrations"),
        help="Directory containing numbered migration SQL files",
    )
    return parser.parse_args()


def forward_migrations(migrations_dir: Path) -> list[Path]:
    migrations = sorted(
        path
        for path in migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.sql")
        if not path.name.endswith(".rollback.sql")
    )
    if not migrations:
        raise RuntimeError(f"no forward migrations found in {migrations_dir}")
    return migrations


def main() -> int:
    args = parse_args()
    migrations_dir = Path(args.migrations_dir)
    for migration in forward_migrations(migrations_dir):
        run_sql_file(migration)
        print(f"applied: {migration.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
