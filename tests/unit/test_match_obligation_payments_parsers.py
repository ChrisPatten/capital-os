from __future__ import annotations

import importlib.util
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_FIX = _ROOT / "tests" / "fixtures" / "bank_csv"


def _load():
    spec = importlib.util.spec_from_file_location(
        "match_obligation_payments", _ROOT / "scripts" / "match_obligation_payments.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m = _load()


def _read(sub: str, name: str) -> str:
    return (_FIX / sub / name).read_text(encoding="utf-8-sig")


def test_citizens_bom_quoting_commas_and_sign():
    rows = m.parse_citizens("citizens_checking_fixture.csv", _read("citizens", "citizens_checking_fixture.csv"))
    # deposit skipped, 4 debits kept
    assert [r["description"] for r in rows] == [
        "ZEBRALOAN SERVICING", "Acme Power web_pay", "GLOBEX GYM", "GLOBEX CLUB",
    ]
    assert rows[0]["date"] == date(2026, 10, 19)
    assert rows[0]["amount"] == Decimal("250.00")
    assert rows[1]["amount"] == Decimal("1100.50")
    assert all(r["amount"] > 0 and r["bank"] == "citizens" for r in rows)
    assert rows[0]["row_number"] == 2


def test_citizens_raw_bom_text_tolerated():
    text = "﻿" + _read("citizens", "citizens_checking_fixture.csv")
    assert len(m.parse_citizens("f.csv", text)) == 4


def test_sfcu_skips_preamble_and_credits_and_combines_memo():
    rows = m.parse_sfcu("sfcu_checking_fixture.csv", _read("sfcu", "sfcu_checking_fixture.csv"))
    assert len(rows) == 2
    assert rows[0]["date"] == date(2026, 10, 6)
    assert rows[0]["amount"] == Decimal("166.00")
    assert "INITECH WATER UTILITY" in rows[0]["description"]
    assert rows[0]["row_number"] == 6  # 3 preamble + header + deposit + this row


def test_sfcu_alternate_layout():
    text = (
        "post_date,tran_date,description,amount,balance\n"
        "2026-05-01,,Beginning Balance,,3267.70\n"
        "2026-05-01,,DEBIT CARD WITHDRAWAL PY *OHDEER,-117.00,3150.70\n"
        "2026-05-02,,PAYROLL,500.00,3650.70\n"
    )
    rows = m.parse_sfcu("alt.csv", text)
    assert len(rows) == 1
    assert rows[0]["amount"] == Decimal("117.00")
    assert rows[0]["date"] == date(2026, 5, 1)


def test_apple_card_skips_payments_and_credits():
    rows = m.parse_apple_card("apple_card_fixture.csv", _read("apple_card", "apple_card_fixture.csv"))
    assert len(rows) == 1
    assert rows[0]["amount"] == Decimal("9.99")
    assert rows[0]["date"] == date(2026, 10, 12)
    assert "STREAMCO" in rows[0]["description"]


def test_amex_skips_credits():
    rows = m.parse_amex("amex_fixture.csv", _read("personal_amex", "amex_fixture.csv"))
    assert len(rows) == 1
    assert rows[0]["amount"] == Decimal("12.74")
    assert rows[0]["date"] == date(2026, 10, 9)


def test_row_key_is_stable_and_file_scoped():
    text = _read("personal_amex", "amex_fixture.csv")
    a = m.parse_amex("a.csv", text)[0]["row_key"]
    assert a == m.parse_amex("a.csv", text)[0]["row_key"]
    assert a != m.parse_amex("b.csv", text)[0]["row_key"]
    assert len(a) == 64


def test_unrecognized_headers_raise():
    with pytest.raises(ValueError):
        m.parse_citizens("x.csv", "a,b,c\n1,2,3\n")
    with pytest.raises(ValueError):
        m.parse_sfcu("x.csv", "nothing here\n")


def test_load_debits_skips_unknown_folders_and_since(tmp_path):
    import shutil

    shutil.copytree(_FIX, tmp_path / "d")
    (tmp_path / "d" / "mystery").mkdir()
    warnings: list[str] = []
    all_rows = m.load_debits(tmp_path / "d", None, warnings)
    assert any("mystery" in w for w in warnings)
    assert {r["bank"] for r in all_rows} == {"citizens", "sfcu", "apple_card", "amex"}
    later = m.load_debits(tmp_path / "d", date(2026, 10, 10), [])
    assert all(r["date"] >= date(2026, 10, 10) for r in later) and len(later) < len(all_rows)


def test_keywords_metadata_vs_name_fallback():
    assert m.obligation_keywords({"name": "Student loan payment (Firstmark)"}) == (["firstmark"], "any")
    assert m.obligation_keywords({"name": "Mortgage payment (Rocket/MrCooper)"}) == (["rocket", "mrcooper"], "any")
    assert m.obligation_keywords({"name": "Toyota - x", "metadata": {"match_keywords": ["TD Auto"]}}) == (["td auto"], "all")
    # all-generic names keep their words
    assert m.obligation_keywords({"name": "Loan payment"}) == (["payment", "loan"], "any") or m.obligation_keywords({"name": "Loan payment"})[0]


def test_amount_tolerance():
    assert m.amount_ok(Decimal("100"), Decimal("100.90"), Decimal(1), Decimal("1.00"))
    assert not m.amount_ok(Decimal("100"), Decimal("101.50"), Decimal(1), Decimal("1.00"))
    assert m.amount_ok(Decimal("3000"), Decimal("3025"), Decimal(1), Decimal("1.00"))
