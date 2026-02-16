#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from capital_os.db.coa_importer import CoaImportError, import_coa_file, validate_coa_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate or seed Chart of Accounts YAML for Capital OS bootstrap")
    parser.add_argument("path", help="Path to COA YAML file (for example: config/coa.yaml)")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate COA YAML and exit without DB changes",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and compute changes without persisting writes",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.validate_only:
            validate_coa_file(args.path)
            print("coa validate (ok)")
            return 0
        summary = import_coa_file(args.path, dry_run=args.dry_run)
    except FileNotFoundError:
        print(f"error: file not found: {args.path}", file=sys.stderr)
        return 2
    except CoaImportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    mode = "dry-run" if args.dry_run else "apply"
    print(f"coa import ({mode})")
    print(f"created={summary.created} updated={summary.updated} unchanged={summary.unchanged}")
    for warning in summary.warnings:
        print(f"warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
