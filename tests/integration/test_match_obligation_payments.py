from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

from capital_os.config import get_settings
from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.runtime.execute_tool import execute_tool

_ROOT = Path(__file__).resolve().parents[2]
_FIXTURES = _ROOT / "tests" / "fixtures" / "bank_csv"

_spec = importlib.util.spec_from_file_location(
    "match_obligation_payments", _ROOT / "scripts" / "match_obligation_payments.py"
)
script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(script)

_n = {"n": 0}


def _call(tool, payload):
    _n["n"] += 1
    payload = {"correlation_id": f"t-{_n['n']}", **payload}
    res = execute_tool(tool, payload, actor_id="t", authn_method="t", authorization_result="t")
    assert res.success, res.payload
    return res.payload


def _db_path() -> str:
    return get_settings().db_url.removeprefix("sqlite:///")


def _upsert(account_id, name, amount, due, **extra):
    return _call(
        "create_or_update_obligation",
        {
            "source_system": "pytest",
            "name": name,
            "account_id": account_id,
            "cadence": "monthly",
            "expected_amount": amount,
            "next_due_date": due,
            **extra,
        },
    )["obligation_id"]


@pytest.fixture
def seeded(db_available):
    if not db_available:
        pytest.skip("database unavailable")
    with transaction() as conn:
        acct = create_account(conn, {"code": "2900", "name": "Payables", "account_type": "liability"})
    ids = {
        "recurring": _upsert(acct, "Student note (Zebraloan)", "250.0000", "2026-10-20",
                             recurrence="monthly", day_of_month=20),
        "one_time": _upsert(acct, "Initech water bill", "166.0000", "2026-10-06"),
        "keywords": _upsert(acct, "Entertainment bundle", "9.99", "2026-10-12",
                            metadata={"match_keywords": ["streamco", "monthly"]}),
        "ambiguous": _upsert(acct, "Globex membership", "30.0000", "2026-10-05"),
        "nodebit": _upsert(acct, "Hooli subscription", "55.0000", "2026-10-10"),
    }
    return ids


def _run(capsys, *extra):
    code = script.main(["--db-path", _db_path(), "--data-dir", str(_FIXTURES), "--json", *extra])
    out = capsys.readouterr().out
    return code, json.loads(out)


def _counts():
    conn = sqlite3.connect(_db_path())
    try:
        return {
            t: conn.execute(f"select count(*) from {t}").fetchone()[0]
            for t in ("ledger_transactions", "ledger_postings")
        }
    finally:
        conn.close()


def _obligation_state():
    conn = sqlite3.connect(_db_path())
    try:
        return conn.execute(
            "select obligation_id, active, next_due_date, fulfilled_at from obligations order by obligation_id"
        ).fetchall()
    finally:
        conn.close()


def test_dry_run_proposes_but_changes_nothing(seeded, capsys):
    before = _obligation_state()
    code, report = _run(capsys)
    assert code == 0 and report["mode"] == "dry-run"
    proposed = {p["obligation_id"]: p for p in report["proposed"]}
    assert set(proposed) == {seeded["recurring"], seeded["one_time"], seeded["keywords"]}
    assert all("result" not in p for p in proposed.values())
    assert [a["obligation_id"] for a in report["ambiguous"]] == [seeded["ambiguous"]]
    assert [u["obligation_id"] for u in report["unmatched"]] == [seeded["nodebit"]]
    assert _obligation_state() == before


def test_apply_fulfills_and_replay_is_noop(seeded, capsys):
    ledger_before = _counts()
    code, report = _run(capsys, "--apply")
    assert code == 0 and report["mode"] == "apply"
    results = {p["obligation_id"]: p["result"]["status"] for p in report["proposed"]}
    assert set(results.values()) == {"fulfilled"} and len(results) == 3

    state = {r[0]: r for r in _obligation_state()}
    rec = state[seeded["recurring"]]
    assert rec[1] == 1 and rec[2] == "2026-11-20"  # rolled forward, still active
    assert state[seeded["one_time"]][1] == 0  # deactivated
    assert state[seeded["ambiguous"]][1] == 1 and state[seeded["ambiguous"]][2] == "2026-10-05"
    assert state[seeded["nodebit"]][3] is None

    after_first = _obligation_state()
    code, report2 = _run(capsys, "--apply")
    assert code == 0
    # recurring row moved on and the one-time row is inactive: nothing proposed, nothing changes
    assert report2["proposed"] == []
    assert _obligation_state() == after_first
    assert _counts() == ledger_before


def test_replay_guard_reports_already_fulfilled(seeded, capsys):
    """If a stale proposal is applied twice, the second call is already_fulfilled."""
    obs = script.list_active_obligations()
    ob = next(o for o in obs if o["obligation_id"] == seeded["recurring"])
    debits = script.load_debits(_FIXTURES, None, [])
    found = script.find_matches(
        [ob], debits, tol_pct=1, tol_min=1, days_before=5, days_after=10
    )
    match = found["proposed"][0]
    assert script.apply_match(match)["status"] == "fulfilled"
    assert script.apply_match(match)["status"] == "already_fulfilled"
    state = {r[0]: r for r in _obligation_state()}
    assert state[seeded["recurring"]][2] == "2026-11-20"  # rolled exactly once


def test_ambiguous_not_applied_and_no_ledger_writes(seeded, capsys):
    before = _counts()
    _run(capsys, "--apply")
    assert _counts() == before
    state = {r[0]: r for r in _obligation_state()}
    assert state[seeded["ambiguous"]][1] == 1


def test_human_readable_output_and_exit_codes(seeded, capsys, tmp_path):
    code = script.main(["--db-path", _db_path(), "--data-dir", str(_FIXTURES)])
    out = capsys.readouterr().out
    assert code == 0 and "DRY RUN" in out and "summary:" in out
    assert script.main(["--db-path", str(tmp_path / "missing.db")]) == 2
    assert script.main(["--db-path", _db_path(), "--data-dir", str(tmp_path / "nope")]) == 2
    assert script.main([]) == 2


def test_since_filters_rows(seeded, capsys):
    code, report = _run(capsys, "--since", "2026-10-15")
    assert code == 0
    # only the 10/19 Zebraloan debit is on/after the cutoff
    assert [p["obligation_id"] for p in report["proposed"]] == [seeded["recurring"]]
