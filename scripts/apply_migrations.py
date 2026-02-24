#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from capital_os.config import get_settings
from capital_os.db.migrations import apply_pending_migrations


def _db_path_from_settings() -> Path:
    db_url = get_settings().db_url
    if not db_url.startswith("sqlite:///"):
        raise ValueError("CAPITAL_OS_DB_URL must use sqlite:/// URL format")
    raw = db_url.removeprefix("sqlite:///")
    if not raw:
        raise ValueError("CAPITAL_OS_DB_URL sqlite path cannot be empty")
    return Path(raw)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply pending SQL migrations in order (idempotent)")
    parser.add_argument(
        "--migrations-dir",
        default=str(ROOT / "migrations"),
        help="Directory containing numbered migration SQL files",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = _db_path_from_settings()
    migrations_dir = Path(args.migrations_dir)

    applied, skipped = apply_pending_migrations(db_path, migrations_dir)

    for name in skipped:
        print(f"skipped (already applied): {name}")
    for name in applied:
        print(f"applied: {name}")

    if not applied and not skipped:
        print("no migrations found")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
