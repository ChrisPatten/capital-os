#!/usr/bin/env python3
"""Offline payment -> obligation auto-matcher (slimming plan item 5).

Reads bank CSV exports, finds debits that match an active obligation (payee
keyword, amount within tolerance, due-date window) and, with ``--apply``, calls
the ``fulfill_obligation`` tool for each unambiguous match. Dry-run by default.

This is deliberately a script and not a runtime feature: the Capital OS runtime
makes no outbound calls and reads no files outside its DB. The script only
touches the ledger DB through ``execute_tool`` (``list_obligations`` and
``fulfill_obligation``). It never records ledger transactions.

Idempotency: every apply call passes ``expected_due_date = next_due_date`` as
read at the start of the run, so a replay against a recurring obligation that
already rolled forward (or a one-time obligation that is now inactive) is a
no-op reported as ``already_fulfilled``. The correlation id is derived from the
CSV row (``automatch-<row_key[:16]>``).

Exit codes: 0 ok; 2 bad arguments or missing paths.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

DEFAULT_DATA_DIR = "/Users/chrispatten/workspace/peggy-claude-code/data/financial"
CENT = Decimal("0.01")

# Words that describe the kind of bill rather than who is being paid. They are
# dropped from the name-derived keywords so "loan" / "payment" / "insurance"
# do not match every unrelated debit. If dropping them leaves nothing, they are
# kept (a name made only of generic words still needs some keyword).
GENERIC_WORDS = frozenset(
    {
        "payment", "payments", "loan", "loans", "insurance", "mortgage", "card", "cards",
        "bill", "bills", "annual", "monthly", "quarterly", "tax", "taxes", "lease",
        "wireless", "internet", "electric", "water", "paydown", "statement", "account",
        "the", "and", "autopay", "auto", "student", "personal",
    }
)

BANK_DIRS = {
    "citizens": "citizens",
    "sfcu": "sfcu",
    "apple_card": "apple_card",
    "personal_amex": "amex",
}


# --------------------------------------------------------------------------
# Parsers (pure)
# --------------------------------------------------------------------------

def _row_key(bank: str, file_name: str, raw: str) -> str:
    return hashlib.sha256(f"{bank}\n{file_name}\n{raw}".encode("utf-8")).hexdigest()


def _money(text: str) -> Decimal | None:
    cleaned = (text or "").strip().replace("$", "").replace(",", "").replace(" ", "")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _parse_date(text: str, fmts: tuple[str, ...]) -> date | None:
    text = (text or "").strip()
    for fmt in fmts:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _lines(text: str) -> list[str]:
    return text.lstrip("﻿").splitlines()


def _split(line: str) -> list[str]:
    return next(csv.reader([line]), [])


def _debit(bank, file_name, row_number, raw, dt, description, amount) -> dict:
    return {
        "bank": bank,
        "file": file_name,
        "row_number": row_number,
        "date": dt,
        "description": " ".join(description.split()),
        "amount": amount.quantize(CENT),
        "row_key": _row_key(bank, file_name, raw),
    }


def _header_index(header: list[str]) -> dict[str, int]:
    return {h.strip().lower(): i for i, h in enumerate(header)}


def _cell(cells: list[str], idx: dict[str, int], name: str) -> str:
    i = idx.get(name)
    return cells[i] if i is not None and i < len(cells) else ""


def parse_citizens(file_name: str, text: str) -> list[dict]:
    lines = _lines(text)
    if not lines:
        return []
    idx = _header_index(_split(lines[0]))
    if not {"date", "description", "amount"} <= idx.keys():
        raise ValueError("unrecognized Citizens header")
    out = []
    for n, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        cells = _split(line)
        dt = _parse_date(_cell(cells, idx, "date"), ("%m/%d/%y", "%m/%d/%Y"))
        amt = _money(_cell(cells, idx, "amount"))
        if dt is None or amt is None or amt >= 0:
            continue
        out.append(_debit("citizens", file_name, n, line, dt, _cell(cells, idx, "description"), -amt))
    return out


def parse_sfcu(file_name: str, text: str) -> list[dict]:
    lines = _lines(text)
    start = next((i for i, ln in enumerate(lines) if ln.startswith("Transaction Number,")), None)
    if start is None:
        # Alternate hand-exported layout seen in some months:
        # post_date,tran_date,description,amount,balance (ISO dates, debit negative).
        alt = next((i for i, ln in enumerate(lines) if ln.lower().startswith("post_date,")), None)
        if alt is None:
            raise ValueError("unrecognized SFCU header")
        return _parse_sfcu_alt(file_name, lines, alt)
    idx = _header_index(_split(lines[start]))
    out = []
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if not line.strip():
            continue
        cells = _split(line)
        dt = _parse_date(_cell(cells, idx, "date"), ("%m/%d/%Y", "%m/%d/%y"))
        amt = _money(_cell(cells, idx, "amount debit"))
        if dt is None or amt is None or amt == 0:
            continue
        desc = f"{_cell(cells, idx, 'description')} {_cell(cells, idx, 'memo')}"
        out.append(_debit("sfcu", file_name, i + 1, line, dt, desc, abs(amt)))
    return out


def _parse_sfcu_alt(file_name: str, lines: list[str], start: int) -> list[dict]:
    idx = _header_index(_split(lines[start]))
    out = []
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if not line.strip():
            continue
        cells = _split(line)
        dt = _parse_date(_cell(cells, idx, "post_date"), ("%Y-%m-%d", "%m/%d/%Y"))
        amt = _money(_cell(cells, idx, "amount"))
        if dt is None or amt is None or amt >= 0:
            continue
        out.append(_debit("sfcu", file_name, i + 1, line, dt, _cell(cells, idx, "description"), -amt))
    return out


def parse_apple_card(file_name: str, text: str) -> list[dict]:
    lines = _lines(text)
    if not lines:
        return []
    idx = _header_index(_split(lines[0]))
    if not {"transaction date", "description", "amount (usd)", "type"} <= idx.keys():
        raise ValueError("unrecognized Apple Card header")
    out = []
    for n, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        cells = _split(line)
        kind = _cell(cells, idx, "type").strip().lower()
        if kind in ("payment", "credit"):
            continue
        dt = _parse_date(_cell(cells, idx, "transaction date"), ("%m/%d/%Y", "%m/%d/%y"))
        amt = _money(_cell(cells, idx, "amount (usd)"))
        if dt is None or amt is None or amt <= 0:
            continue
        desc = f"{_cell(cells, idx, 'description')} {_cell(cells, idx, 'merchant')}"
        out.append(_debit("apple_card", file_name, n, line, dt, desc, amt))
    return out


def parse_amex(file_name: str, text: str) -> list[dict]:
    lines = _lines(text)
    if not lines:
        return []
    idx = _header_index(_split(lines[0]))
    if not {"date", "description", "amount"} <= idx.keys():
        raise ValueError("unrecognized Amex header")
    out = []
    for n, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        cells = _split(line)
        dt = _parse_date(_cell(cells, idx, "date"), ("%m/%d/%Y", "%m/%d/%y"))
        amt = _money(_cell(cells, idx, "amount"))
        if dt is None or amt is None or amt <= 0:
            continue
        out.append(_debit("amex", file_name, n, line, dt, _cell(cells, idx, "description"), amt))
    return out


PARSERS = {
    "citizens": parse_citizens,
    "sfcu": parse_sfcu,
    "apple_card": parse_apple_card,
    "personal_amex": parse_amex,
}


def load_debits(data_dir: Path, since: date | None, warnings: list[str]) -> list[dict]:
    debits: list[dict] = []
    for sub in sorted(p for p in data_dir.iterdir() if p.is_dir()):
        parser = PARSERS.get(sub.name)
        if parser is None:
            warnings.append(f"skipping unknown folder: {sub.name}")
            continue
        for csv_path in sorted(sub.glob("*.csv")):
            try:
                rows = parser(csv_path.name, csv_path.read_text(encoding="utf-8-sig"))
            except (ValueError, OSError) as exc:
                warnings.append(f"skipping {sub.name}/{csv_path.name}: {exc}")
                continue
            debits.extend(rows)
    if since is not None:
        debits = [d for d in debits if d["date"] >= since]
    return debits


# --------------------------------------------------------------------------
# Matching (pure)
# --------------------------------------------------------------------------

def _words(text: str) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9]+", text.lower()) if len(w) >= 4]


def obligation_keywords(obligation: dict) -> tuple[list[str], str]:
    """Return (keywords, mode). mode is ``all`` for explicit metadata keywords
    (every keyword must appear) and ``any`` for name-derived keywords (one is
    enough).

    Name fallback: take the whole name (text before `` - `` is the label, and
    the text inside parentheses is kept because real names look like
    ``Student loan payment (Firstmark)`` where the payee lives in the
    parentheses), lowercase, split into words of length >= 4, drop generic bill
    words (payment, loan, insurance, ...). If nothing is left, keep them all.
    """
    meta = obligation.get("metadata") or {}
    explicit = meta.get("match_keywords")
    if isinstance(explicit, list) and explicit:
        return [str(k).lower() for k in explicit if str(k).strip()], "all"
    name = str(obligation.get("name", "")).split(" - ")[0]
    words = _words(name)
    specific = [w for w in words if w not in GENERIC_WORDS]
    return list(dict.fromkeys(specific or words)), "any"


def amount_ok(expected: Decimal, actual: Decimal, tol_pct: Decimal, tol_min: Decimal) -> bool:
    tol = max(tol_min, expected * tol_pct / Decimal(100))
    return abs(actual - expected) <= tol


def debit_matches(obligation: dict, debit: dict, tol_pct, tol_min, days_before, days_after) -> bool:
    keywords, mode = obligation_keywords(obligation)
    if not keywords:
        return False
    desc = debit["description"].lower()
    hits = [k in desc for k in keywords]
    if not (all(hits) if mode == "all" else any(hits)):
        return False
    if not amount_ok(Decimal(str(obligation["expected_amount"])), debit["amount"], tol_pct, tol_min):
        return False
    due = date.fromisoformat(str(obligation["next_due_date"]))
    return due - timedelta(days=days_before) <= debit["date"] <= due + timedelta(days=days_after)


def find_matches(obligations, debits, *, tol_pct, tol_min, days_before, days_after) -> dict:
    """Classify into proposed / ambiguous / unmatched."""
    cand: dict[str, list[dict]] = {}
    claimed_by: dict[str, set[str]] = {}
    for ob in obligations:
        rows = [d for d in debits if debit_matches(ob, d, tol_pct, tol_min, days_before, days_after)]
        cand[ob["obligation_id"]] = rows
        for d in rows:
            claimed_by.setdefault(d["row_key"], set()).add(ob["obligation_id"])

    proposed, ambiguous, unmatched = [], [], []
    latest = max((d["date"] for d in debits), default=None)
    for ob in obligations:
        rows = cand[ob["obligation_id"]]
        if len(rows) == 1 and len(claimed_by[rows[0]["row_key"]]) == 1:
            proposed.append({"obligation": ob, "debit": rows[0]})
        elif rows:
            reason = (
                "multiple candidate debits"
                if len(rows) > 1
                else "debit also matches other obligations"
            )
            ambiguous.append({"obligation": ob, "debits": rows, "reason": reason})
        else:
            due = date.fromisoformat(str(ob["next_due_date"]))
            if latest is not None and due - timedelta(days=days_before) <= latest:
                unmatched.append({"obligation": ob})
    return {"proposed": proposed, "ambiguous": ambiguous, "unmatched": unmatched}


# --------------------------------------------------------------------------
# Runtime (imports capital_os only after the DB path is configured)
# --------------------------------------------------------------------------

def _tool(name: str, payload: dict) -> dict:
    from capital_os.cli.context import (
        CLI_ACTOR_ID,
        CLI_AUTHN_METHOD,
        CLI_AUTHORIZATION_RESULT,
    )
    from capital_os.runtime.execute_tool import execute_tool

    result = execute_tool(
        name,
        payload,
        actor_id=CLI_ACTOR_ID,
        authn_method=CLI_AUTHN_METHOD,
        authorization_result=CLI_AUTHORIZATION_RESULT,
    )
    if not result.success:
        raise RuntimeError(f"{name} failed: {json.dumps(result.payload)[:300]}")
    return result.payload


def list_active_obligations() -> list[dict]:
    out, cursor, page = [], None, 0
    while True:
        page += 1
        payload = {"limit": 500, "active_only": True, "correlation_id": f"automatch-list-{page}"}
        if cursor:
            payload["cursor"] = cursor
        res = _tool("list_obligations", payload)
        out.extend(res["obligations"])
        cursor = res.get("next_cursor")
        if not cursor:
            return out


def apply_match(match: dict) -> dict:
    ob, d = match["obligation"], match["debit"]
    res = _tool(
        "fulfill_obligation",
        {
            "obligation_id": ob["obligation_id"],
            "expected_due_date": str(ob["next_due_date"]),
            "fulfilled_at": f"{d['date'].isoformat()}T12:00:00Z",
            "correlation_id": "automatch-" + d["row_key"][:16],
        },
    )
    return {"status": res["status"], "next_due_date": res.get("next_due_date")}


def _match_view(m: dict) -> dict:
    ob, d = m["obligation"], m["debit"]
    return {
        "obligation_id": ob["obligation_id"],
        "obligation": ob["name"],
        "expected_amount": str(Decimal(str(ob["expected_amount"])).quantize(CENT)),
        "next_due_date": str(ob["next_due_date"]),
        "bank": d["bank"],
        "file": d["file"],
        "row_number": d["row_number"],
        "row_key": d["row_key"],
        "date": d["date"].isoformat(),
        "description": d["description"],
        "amount": str(d["amount"]),
    }


def run(args) -> dict:
    warnings: list[str] = []
    debits = load_debits(Path(args.data_dir), args.since, warnings)
    obligations = list_active_obligations()
    found = find_matches(
        obligations,
        debits,
        tol_pct=Decimal(str(args.amount_tolerance_pct)),
        tol_min=Decimal(str(args.amount_tolerance_min)),
        days_before=args.days_before,
        days_after=args.days_after,
    )
    proposed = [_match_view(m) for m in found["proposed"]]
    if args.apply:
        for view, m in zip(proposed, found["proposed"]):
            view["result"] = apply_match(m)
    ambiguous = [
        {
            "obligation_id": a["obligation"]["obligation_id"],
            "obligation": a["obligation"]["name"],
            "next_due_date": str(a["obligation"]["next_due_date"]),
            "reason": a["reason"],
            "candidates": [
                {"date": d["date"].isoformat(), "amount": str(d["amount"]),
                 "description": d["description"], "bank": d["bank"]}
                for d in a["debits"]
            ],
        }
        for a in found["ambiguous"]
    ]
    unmatched = [
        {
            "obligation_id": u["obligation"]["obligation_id"],
            "obligation": u["obligation"]["name"],
            "expected_amount": str(Decimal(str(u["obligation"]["expected_amount"])).quantize(CENT)),
            "next_due_date": str(u["obligation"]["next_due_date"]),
        }
        for u in found["unmatched"]
    ]
    return {
        "mode": "apply" if args.apply else "dry-run",
        "debits_considered": len(debits),
        "active_obligations": len(obligations),
        "proposed": proposed,
        "ambiguous": ambiguous,
        "unmatched": unmatched,
        "warnings": warnings,
    }


def render(report: dict) -> str:
    lines = []
    if report["mode"] == "dry-run":
        lines.append("*** DRY RUN: no changes made. Re-run with --apply to fulfill the proposed matches. ***")
    else:
        lines.append("*** APPLY MODE: fulfill_obligation was called for each proposed match. ***")
    for w in report["warnings"]:
        lines.append(f"warning: {w}")
    lines.append("")
    lines.append(f"PROPOSED ({len(report['proposed'])})")
    for p in report["proposed"]:
        res = f"  -> {p['result']['status']}" if "result" in p else ""
        lines.append(
            f"  {p['obligation'][:40]:<40} due {p['next_due_date']}  "
            f"exp {p['expected_amount']:>10}  <=  {p['date']} {p['amount']:>10} "
            f"[{p['bank']}] {p['description'][:50]}{res}"
        )
    lines.append("")
    lines.append(f"AMBIGUOUS ({len(report['ambiguous'])}) - not applied")
    for a in report["ambiguous"]:
        lines.append(f"  {a['obligation'][:40]:<40} due {a['next_due_date']}  ({a['reason']})")
        for c in a["candidates"]:
            lines.append(f"      {c['date']} {c['amount']:>10} [{c['bank']}] {c['description'][:60]}")
    lines.append("")
    lines.append(f"UNMATCHED OBLIGATIONS IN WINDOW ({len(report['unmatched'])})")
    for u in report["unmatched"]:
        lines.append(f"  {u['obligation'][:40]:<40} due {u['next_due_date']}  exp {u['expected_amount']:>10}")
    lines.append("")
    lines.append(
        f"summary: mode={report['mode']} debits={report['debits_considered']} "
        f"obligations={report['active_obligations']} proposed={len(report['proposed'])} "
        f"ambiguous={len(report['ambiguous'])} unmatched={len(report['unmatched'])}"
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Match bank-CSV debits to active obligations (offline).")
    p.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    p.add_argument("--db-path", required=True)
    p.add_argument("--apply", action="store_true", help="Call fulfill_obligation (default: dry-run).")
    p.add_argument("--amount-tolerance-pct", type=Decimal, default=Decimal(1))
    p.add_argument("--amount-tolerance-min", type=Decimal, default=Decimal("1.00"))
    p.add_argument("--days-before", type=int, default=5)
    p.add_argument("--days-after", type=int, default=10)
    p.add_argument("--since", type=date.fromisoformat, default=None)
    p.add_argument("--json", action="store_true", dest="as_json")
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    if not Path(args.data_dir).is_dir():
        print(f"error: data dir not found: {args.data_dir}", file=sys.stderr)
        return 2
    db = Path(args.db_path)
    if not db.is_file():
        print(f"error: database file not found: {args.db_path}", file=sys.stderr)
        return 2

    os.environ["CAPITAL_OS_DB_URL"] = f"sqlite:///{db.resolve()}"
    from capital_os.config import get_settings

    get_settings.cache_clear()

    report = run(args)
    print(json.dumps(report, indent=2) if args.as_json else render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
