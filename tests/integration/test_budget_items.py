from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import app
from capital_os.config import get_settings
from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account
from tests.support.auth import AUTH_HEADERS, READ_ONLY_AUTH_HEADERS

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
def account_id(db_available):
    if not db_available:
        pytest.skip("database unavailable")
    with transaction() as conn:
        return create_account(conn, {"code": "1410", "name": "Budget Checking", "account_type": "asset"})


def _body(**extra):
    body = {
        "item_key": "mortgage",
        "name": "Mortgage",
        "direction": "outflow",
        "amount": "3127.46",
        "cadence": "monthly",
        "day_of_month": 3,
        "bucket": "recurring",
        "effective_date": "2026-10-01",
        "correlation_id": _corr("bud"),
    }
    body.update(extra)
    return body


def _upsert(client, **extra):
    resp = client.post("/tools/upsert_budget_item", json=_body(**extra))
    assert resp.status_code == 200, resp.text
    return resp.json()


def _rows():
    conn = sqlite3.connect(get_settings().db_url.removeprefix("sqlite:///"))
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute("SELECT * FROM budget_items ORDER BY created_at, rowid").fetchall()
    finally:
        conn.close()


def test_create_version_unchanged_and_history(client, account_id):
    first = _upsert(client, account_id=account_id)
    assert first["status"] == "created" and first["active"] is True

    same = _upsert(client, account_id=account_id)
    assert same["status"] == "unchanged"
    assert same["item_id"] == first["item_id"]
    assert len(_rows()) == 1

    changed = _upsert(client, account_id=account_id, amount="3200.00", effective_date="2026-11-01")
    assert changed["status"] == "versioned"
    assert changed["item_id"] != first["item_id"]

    rows = _rows()
    assert len(rows) == 2
    assert sorted(r["active"] for r in rows) == [0, 1]
    by_id = {r["item_id"]: r for r in rows}
    assert by_id[first["item_id"]]["active"] == 0
    assert by_id[changed["item_id"]]["active"] == 1

    listed = client.post(
        "/tools/list_budget_items", json={"correlation_id": _corr("l"), "active_only": False}
    ).json()
    assert len(listed["items"]) == 2
    active = client.post("/tools/list_budget_items", json={"correlation_id": _corr("l")}).json()
    assert [i["item_id"] for i in active["items"]] == [changed["item_id"]]
    assert active["items"][0]["amount"] == "3200.0000"


def test_deactivate_and_noop_deactivate(client):
    created = _upsert(client)
    off = _upsert(client, active=False)
    assert off["status"] == "deactivated" and off["item_id"] == created["item_id"] and off["active"] is False
    again = _upsert(client, active=False)
    assert again["status"] == "unchanged"
    resp = client.post("/tools/upsert_budget_item", json=_body(item_key="never-existed", active=False))
    assert resp.status_code == 400
    # An inactive key can be recreated as a fresh version.
    back = _upsert(client)
    assert back["status"] == "versioned" and back["item_id"] != created["item_id"]


@pytest.mark.parametrize(
    "extra",
    [
        {"bucket": None},  # outflow without bucket
        {"direction": "inflow"},  # inflow with bucket
        {"day_of_month": None},  # monthly without day
        {"cadence": "biweekly", "day_of_month": None},  # biweekly without anchor
        {"cadence": "annual", "day_of_month": None, "anchor_date": None},
        {"amount": "-1.00"},
        {"cadence": "weekly"},
    ],
)
def test_validation_failures_return_422(client, extra):
    resp = client.post("/tools/upsert_budget_item", json=_body(**extra))
    assert resp.status_code == 422, resp.text
    assert len(_rows()) == 0


def test_unknown_account_returns_400_and_writes_nothing(client):
    resp = client.post("/tools/upsert_budget_item", json=_body(account_id="does-not-exist"))
    assert resp.status_code == 400
    assert len(_rows()) == 0


def test_trigger_blocks_direct_update_delete_and_reactivation(client):
    created = _upsert(client)
    conn = sqlite3.connect(get_settings().db_url.removeprefix("sqlite:///"))
    try:
        with pytest.raises(sqlite3.DatabaseError, match="budget_items UPDATE not permitted"):
            conn.execute("UPDATE budget_items SET amount='1.0000' WHERE item_id=?", (created["item_id"],))
        with pytest.raises(sqlite3.DatabaseError, match="DELETE not permitted"):
            conn.execute("DELETE FROM budget_items WHERE item_id=?", (created["item_id"],))
        conn.execute("UPDATE budget_items SET active=0 WHERE item_id=?", (created["item_id"],))
        with pytest.raises(sqlite3.DatabaseError, match="UPDATE not permitted"):
            conn.execute("UPDATE budget_items SET active=1 WHERE item_id=?", (created["item_id"],))
    finally:
        conn.close()


def test_partial_unique_index_allows_one_active_version(client):
    _upsert(client)
    conn = sqlite3.connect(get_settings().db_url.removeprefix("sqlite:///"))
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO budget_items (item_id,item_key,name,direction,amount,cadence,day_of_month,bucket,effective_date)"
                " VALUES ('dup','mortgage','x','outflow',1,'monthly',1,'recurring','2026-10-02')"
            )
    finally:
        conn.close()


def test_pagination_and_filters(client, account_id):
    for i in range(5):
        _upsert(client, item_key=f"k{i}", name=f"n{i}", amount=f"{i + 1}.00", account_id=account_id if i < 2 else None)
    _upsert(client, item_key="pay", name="Pay", direction="inflow", bucket=None, cadence="biweekly", day_of_month=None,
            anchor_date="2026-10-29", amount="100.00")
    page1 = client.post("/tools/list_budget_items", json={"correlation_id": _corr("p"), "limit": 3}).json()
    assert len(page1["items"]) == 3 and page1["next_cursor"]
    page2 = client.post(
        "/tools/list_budget_items", json={"correlation_id": _corr("p"), "limit": 3, "cursor": page1["next_cursor"]}
    ).json()
    assert len(page2["items"]) == 3 and page2["next_cursor"] is None
    keys = [i["item_key"] for i in page1["items"] + page2["items"]]
    assert keys == sorted(keys) and len(set(keys)) == 6
    inflows = client.post("/tools/list_budget_items", json={"correlation_id": _corr("p"), "direction": "inflow"}).json()
    assert [i["item_key"] for i in inflows["items"]] == ["pay"]
    by_acct = client.post("/tools/list_budget_items", json={"correlation_id": _corr("p"), "account_id": account_id}).json()
    assert len(by_acct["items"]) == 2
    by_bucket = client.post("/tools/list_budget_items", json={"correlation_id": _corr("p"), "bucket": "debt"}).json()
    assert by_bucket["items"] == []


def test_reader_can_read_but_not_upsert(db_available):
    if not db_available:
        pytest.skip("database unavailable")
    reader = TestClient(app, headers=READ_ONLY_AUTH_HEADERS)
    assert reader.post("/tools/upsert_budget_item", json=_body()).status_code == 403
    assert reader.post("/tools/list_budget_items", json={"correlation_id": _corr("r")}).status_code == 200
    assert reader.post("/tools/get_budget_summary", json={"correlation_id": _corr("r")}).status_code == 200


def test_schema_objects_exist(db_available):
    if not db_available:
        pytest.skip("database unavailable")
    conn = sqlite3.connect(get_settings().db_url.removeprefix("sqlite:///"))
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(budget_items)")}
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE tbl_name='budget_items'")}
    finally:
        conn.close()
    assert {"item_id", "item_key", "direction", "amount", "cadence", "anchor_date", "bucket", "effective_date"} <= cols
    assert {"budget_items_versioned_update_guard", "budget_items_no_delete", "idx_budget_items_active_key"} <= names
