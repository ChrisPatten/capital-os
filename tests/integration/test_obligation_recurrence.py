from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import app
from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.observability.hashing import payload_hash
from tests.support.auth import AUTH_HEADERS

_counter = {"n": 0}


def _corr(prefix: str) -> str:
    _counter["n"] += 1
    return f"{prefix}-{_counter['n']}"


@pytest.fixture
def client(db_available):
    if not db_available:
        pytest.skip("database unavailable")
    return TestClient(app, headers=AUTH_HEADERS)


@pytest.fixture
def accounts(db_available):
    if not db_available:
        pytest.skip("database unavailable")
    with transaction() as conn:
        liability = create_account(conn, {"code": "2310", "name": "Mortgage", "account_type": "liability"})
        funding = create_account(conn, {"code": "1310", "name": "Checking", "account_type": "asset"})
    return liability, funding


def _upsert(client, account_id, name="Mortgage", due="2026-11-03", **extra):
    payload = {
        "source_system": "pytest",
        "name": name,
        "account_id": account_id,
        "cadence": "monthly",
        "expected_amount": "3127.4600",
        "next_due_date": due,
        "metadata": {"k": "v"},
        "correlation_id": _corr("up"),
        **extra,
    }
    resp = client.post("/tools/create_or_update_obligation", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["obligation_id"]


def _fulfill(client, obligation_id, **extra):
    resp = client.post(
        "/tools/fulfill_obligation",
        json={"obligation_id": obligation_id, "correlation_id": _corr("ful"), **extra},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _row(obligation_id):
    with transaction() as conn:
        return dict(conn.execute("SELECT * FROM obligations WHERE obligation_id=?", (obligation_id,)).fetchone())


def test_migration_adds_recurrence_columns(db_available):
    if not db_available:
        pytest.skip("database unavailable")
    with transaction() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(obligations)").fetchall()}
    assert {"recurrence", "day_of_month", "funding_account_id", "bucket"} <= cols


def test_monthly_recurrence_rolls_forward_and_stays_active(client, accounts):
    liability, funding = accounts
    oid = _upsert(
        client, liability, recurrence="monthly", day_of_month=3, funding_account_id=funding, bucket="recurring"
    )
    body = _fulfill(client, oid, fulfilled_by_transaction_id="txn-1")
    assert body["status"] == "fulfilled"
    assert body["next_due_date"] == "2026-12-03"
    row = _row(oid)
    assert row["active"] == 1
    assert row["next_due_date"] == "2026-12-03"
    assert row["fulfilled_by_transaction_id"] == "txn-1"
    assert row["fulfilled_at"] is not None


def test_month_end_day_clamps_then_recovers(client, accounts):
    liability, _ = accounts
    oid = _upsert(client, liability, due="2026-01-31", recurrence="monthly", day_of_month=31)
    assert _fulfill(client, oid)["next_due_date"] == "2026-02-28"
    assert _fulfill(client, oid)["next_due_date"] == "2026-03-31"


def test_biweekly_adds_fourteen_days(client, accounts):
    liability, _ = accounts
    oid = _upsert(client, liability, due="2026-10-29", recurrence="biweekly")
    assert _fulfill(client, oid)["next_due_date"] == "2026-11-12"
    assert _row(oid)["active"] == 1


def test_quarterly_and_annual(client, accounts):
    liability, _ = accounts
    q = _upsert(client, liability, name="Water", due="2026-11-15", recurrence="quarterly")
    a = _upsert(client, liability, name="Excise", due="2026-10-01", recurrence="annual", bucket="annual")
    assert _fulfill(client, q)["next_due_date"] == "2027-02-15"
    assert _fulfill(client, a)["next_due_date"] == "2027-10-01"


@pytest.mark.parametrize("extra", [{}, {"recurrence": "one_time"}])
def test_one_time_and_null_recurrence_deactivate_as_before(client, accounts, extra):
    liability, _ = accounts
    oid = _upsert(client, liability, name=f"Bill {extra}", **extra)
    body = _fulfill(client, oid, fulfilled_by_transaction_id="txn-9")
    assert body["status"] == "fulfilled"
    assert body["next_due_date"] is None
    row = _row(oid)
    assert row["active"] == 0
    assert row["next_due_date"] == "2026-11-03"
    again = _fulfill(client, oid)
    assert again["status"] == "already_fulfilled"
    assert row == _row(oid)


def test_expected_due_date_guard_prevents_double_roll(client, accounts):
    liability, _ = accounts
    oid = _upsert(client, liability, recurrence="monthly", day_of_month=3)
    first = _fulfill(client, oid, expected_due_date="2026-11-03", fulfilled_by_transaction_id="txn-a")
    assert first["status"] == "fulfilled"
    before = _row(oid)
    replay = _fulfill(client, oid, expected_due_date="2026-11-03", fulfilled_by_transaction_id="txn-b")
    assert replay["status"] == "already_fulfilled"
    assert replay["next_due_date"] == "2026-12-03"
    assert replay["fulfilled_by_transaction_id"] == "txn-a"
    assert _row(oid) == before


def test_unguarded_second_fulfill_rolls_again(client, accounts):
    # Documented behavior: without expected_due_date a repeated call advances another cycle.
    liability, _ = accounts
    oid = _upsert(client, liability, recurrence="monthly", day_of_month=3)
    _fulfill(client, oid)
    assert _fulfill(client, oid)["next_due_date"] == "2027-01-03"


def test_unknown_funding_account_is_rejected_with_4xx(client, accounts):
    liability, _ = accounts
    resp = client.post(
        "/tools/create_or_update_obligation",
        json={
            "source_system": "pytest",
            "name": "Bad",
            "account_id": liability,
            "cadence": "monthly",
            "expected_amount": "1.0000",
            "next_due_date": "2026-11-03",
            "funding_account_id": "does-not-exist",
            "correlation_id": _corr("bad"),
        },
    )
    assert resp.status_code == 400
    assert "funding_account_id" in resp.json()["detail"]["message"]
    with transaction() as conn:
        assert conn.execute("SELECT COUNT(*) c FROM obligations").fetchone()["c"] == 0


def test_invalid_recurrence_and_day_rejected(client, accounts):
    liability, _ = accounts
    base = {
        "source_system": "pytest",
        "name": "Bad",
        "account_id": liability,
        "cadence": "monthly",
        "expected_amount": "1.0000",
        "next_due_date": "2026-11-03",
    }
    for extra in ({"recurrence": "weekly"}, {"day_of_month": 32}, {"bucket": "nope"}):
        resp = client.post(
            "/tools/create_or_update_obligation", json={**base, **extra, "correlation_id": _corr("inv")}
        )
        assert resp.status_code == 422


def test_upsert_without_new_fields_preserves_them_and_explicit_values_update(client, accounts):
    liability, funding = accounts
    oid = _upsert(
        client, liability, recurrence="monthly", day_of_month=3, funding_account_id=funding, bucket="debt"
    )
    same = _upsert(client, liability, due="2026-12-03", expected_amount="9.0000")
    assert same == oid
    row = _row(oid)
    assert (row["recurrence"], row["day_of_month"], row["funding_account_id"], row["bucket"]) == (
        "monthly",
        3,
        funding,
        "debt",
    )
    assert row["next_due_date"] == "2026-12-03"
    _upsert(client, liability, due="2026-12-03", bucket="recurring", day_of_month=5)
    row = _row(oid)
    assert (row["recurrence"], row["day_of_month"], row["bucket"]) == ("monthly", 5, "recurring")
    assert row["funding_account_id"] == funding


def test_list_obligations_returns_new_fields(client, accounts):
    liability, funding = accounts
    _upsert(client, liability, recurrence="monthly", day_of_month=3, funding_account_id=funding, bucket="debt")
    _upsert(client, liability, name="Legacy")
    resp = client.post("/tools/list_obligations", json={"correlation_id": _corr("list")})
    assert resp.status_code == 200
    items = {o["name"]: o for o in resp.json()["obligations"]}
    assert items["Mortgage"]["recurrence"] == "monthly"
    assert items["Mortgage"]["day_of_month"] == 3
    assert items["Mortgage"]["funding_account_id"] == funding
    assert items["Mortgage"]["bucket"] == "debt"
    assert items["Legacy"]["recurrence"] is None


def _event_input_hash(correlation_id: str, tool: str) -> str:
    with transaction() as conn:
        return conn.execute(
            "SELECT input_hash FROM event_log WHERE correlation_id=? AND tool_name=?",
            (correlation_id, tool),
        ).fetchone()["input_hash"]


def test_legacy_payload_hashes_unchanged(client, accounts):
    liability, _ = accounts
    # Legacy create: exactly the keys CreateOrUpdateObligationIn.model_dump() produced pre-0013.
    create_corr = "hash-create"
    create_resp = client.post(
        "/tools/create_or_update_obligation",
        json={
            "source_system": "pytest",
            "name": "Legacy Bill",
            "account_id": liability,
            "cadence": "monthly",
            "expected_amount": "12.5000",
            "next_due_date": "2026-11-03",
            "correlation_id": create_corr,
        },
    )
    assert create_resp.status_code == 200
    from datetime import date
    from decimal import Decimal

    legacy_create = {
        "source_system": "pytest",
        "name": "Legacy Bill",
        "account_id": liability,
        "cadence": "monthly",
        "expected_amount": Decimal("12.5000"),
        "variability_flag": False,
        "next_due_date": date(2026, 11, 3),
        "metadata": {},
        "active": True,
        "entity_id": "entity-default",
        "correlation_id": create_corr,
    }
    assert _event_input_hash(create_corr, "create_or_update_obligation") == payload_hash(legacy_create)

    oid = create_resp.json()["obligation_id"]
    ful_corr = "hash-fulfill"
    assert (
        client.post(
            "/tools/fulfill_obligation",
            json={
                "obligation_id": oid,
                "fulfilled_by_transaction_id": "t1",
                "fulfilled_at": "2026-11-03T12:00:00+00:00",
                "correlation_id": ful_corr,
            },
        ).status_code
        == 200
    )
    legacy_fulfill = {
        "obligation_id": oid,
        "fulfilled_by_transaction_id": "t1",
        "fulfilled_at": "2026-11-03T12:00:00.000000+00:00",
        "correlation_id": ful_corr,
    }
    assert _event_input_hash(ful_corr, "fulfill_obligation") == payload_hash(legacy_fulfill)

    # Legacy list output: rows without the new keys.
    list_resp = client.post("/tools/list_obligations", json={"active_only": False, "correlation_id": "hash-list"})
    body = list_resp.json()
    with transaction() as conn:
        row = conn.execute("SELECT * FROM obligations WHERE obligation_id=?", (oid,)).fetchone()
    legacy_row = {
        "obligation_id": oid,
        "source_system": "pytest",
        "name": "Legacy Bill",
        "account_id": liability,
        "cadence": "monthly",
        "expected_amount": Decimal("12.5000"),
        "variability_flag": False,
        "next_due_date": "2026-11-03",
        "metadata": {},
        "active": False,
        "entity_id": "entity-default",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    assert body["output_hash"] == payload_hash(
        {"obligations": [legacy_row], "next_cursor": None, "correlation_id": "hash-list"}
    )
