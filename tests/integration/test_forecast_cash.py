from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import app
from tests.support.auth import AUTH_HEADERS, READ_ONLY_AUTH_HEADERS
from tests.support.budget_seed import create_budget_accounts, reference_items

D = Decimal


@pytest.fixture
def seeded(db_available):
    if not db_available:
        pytest.skip("database unavailable")
    client = TestClient(app, headers=AUTH_HEADERS)
    acct = create_budget_accounts()
    for i, item in enumerate(reference_items(acct, citizens_payroll="2960.00")):
        resp = client.post("/tools/upsert_budget_item", json={**item, "correlation_id": f"seed-{i}"})
        assert resp.status_code == 200, resp.text
    return client, acct


def _forecast(client, acct, **extra):
    body = {"account_id": acct["citizens"], "as_of_date": "2026-10-19", "days": 163, "correlation_id": "fc-1", **extra}
    return client.post("/tools/forecast_cash", json=body)


def _snapshot(client, acct, day, balance):
    resp = client.post(
        "/tools/record_balance_snapshot",
        json={"source_system": "test", "account_id": acct["citizens"], "snapshot_date": day, "balance": balance,
              "currency": "USD", "correlation_id": f"snap-{day}"},
    )
    assert resp.status_code == 200, resp.text


def test_oct_2026_citizens_model(seeded):
    client, acct = seeded
    resp = _forecast(client, acct, starting_balance="5116.31", threshold="200")
    assert resp.status_code == 200, resp.text
    out = resp.json()
    assert out["end_date"] == "2027-03-31"
    assert out["start"] == {"date": "2026-10-19", "balance": "5116.3100", "source": "explicit", "snapshot_date": None}
    lows = {m["month"]: D(m["min_balance"]) for m in out["monthly_minimums"]}
    assert lows == {
        "2026-10": D("3994.58"), "2026-11": D("2636.74"), "2026-12": D("2506.74"),
        "2027-01": D("2376.74"), "2027-02": D("3120.74"), "2027-03": D("2990.74"),
    }
    assert D(out["overall_minimum"]["balance"]) == D("2376.74")
    assert out["overall_minimum"]["date"] == "2027-01-05"
    assert out["below_threshold"] is False
    assert D(out["threshold"]) == D("200")
    assert out["unposted_events"] is None and out["unscheduled_items"] == []
    # weekend shift: Apple Card paydown nominal Sat 2026-10-24 lands Mon 2026-10-26, ordered by name before Highlander
    oct26 = [e["name"] for e in out["events"] if e["date"] == "2026-10-26"]
    assert oct26 == ["Apple Card paydown", "Highlander"]
    running = D("5116.31")
    for e in out["events"]:
        running += D(e["amount"])
        assert D(e["balance_after"]) == running
        assert (D(e["amount"]) > 0) == (e["direction"] == "inflow")


def test_snapshot_default_and_unposted(seeded):
    client, acct = seeded
    _snapshot(client, acct, "2026-10-16", "5636.75")
    out = _forecast(client, acct, days=10).json()
    assert out["start"]["source"] == "snapshot" and out["start"]["snapshot_date"] == "2026-10-16"
    assert D(out["start"]["balance"]) == D("5636.75") and out["unposted_events"] is None

    # Firstmark (day 18) falls in (snapshot, as_of]; effective_date 2026-10-23 would exclude it, so version it earlier.
    resp = client.post(
        "/tools/upsert_budget_item",
        json={**[i for i in reference_items(acct, "2960.00") if i["item_key"] == "firstmark"][0],
              "effective_date": "2026-10-01", "correlation_id": "fm"},
    )
    assert resp.status_code == 200
    unposted = _forecast(client, acct, days=10, include_unposted=True).json()
    assert [e["name"] for e in unposted["unposted_events"]] == ["Firstmark"]
    assert D(unposted["unposted_events"][0]["amount"]) == D("-520.44")
    assert D(unposted["start"]["balance"]) == D("5116.31")
    # explicit starting_balance ignores include_unposted
    explicit = _forecast(client, acct, days=10, include_unposted=True, starting_balance="100").json()
    assert explicit["unposted_events"] is None and D(explicit["start"]["balance"]) == D("100")


def test_errors(seeded):
    client, acct = seeded
    assert _forecast(client, acct).status_code == 400  # no snapshot, no starting balance
    _snapshot(client, acct, "2026-10-20", "10")
    assert _forecast(client, acct).status_code == 400  # snapshot is after as_of
    bad = client.post("/tools/forecast_cash", json={"account_id": "nope", "as_of_date": "2026-10-19", "days": 5,
                                                    "starting_balance": "1", "correlation_id": "x"})
    assert bad.status_code == 400
    assert _forecast(client, acct, days=0, starting_balance="1").status_code in (400, 422)
    assert _forecast(client, acct, days=731, starting_balance="1").status_code in (400, 422)


def test_obligations_one_time_included_recurring_excluded(seeded):
    client, acct = seeded

    def obligation(name, due, **extra):
        resp = client.post(
            "/tools/create_or_update_obligation",
            json={"source_system": "test", "name": name, "account_id": acct["apple"], "cadence": "custom",
                  "expected_amount": "75.00", "next_due_date": due, "funding_account_id": acct["citizens"],
                  "correlation_id": f"ob-{name}", **extra},
        )
        assert resp.status_code == 200, resp.text

    obligation("Dentist", "2026-11-14")  # Saturday -> Monday 2026-11-16, legacy (recurrence NULL)
    obligation("Permit", "2026-11-20", recurrence="one_time")
    obligation("Gym", "2026-11-21", recurrence="monthly", day_of_month=21, bucket="recurring")
    obligation("Far", "2027-09-01", recurrence="one_time")
    out = _forecast(client, acct, starting_balance="5000", days=60).json()
    obs = [e for e in out["events"] if e["kind"] == "obligation"]
    assert [(e["name"], e["date"], D(e["amount"])) for e in obs] == [
        ("Dentist", "2026-11-16", D("-75")), ("Permit", "2026-11-20", D("-75"))
    ]


def test_reader_token_allowed(seeded):
    client, acct = seeded
    reader = TestClient(app, headers=READ_ONLY_AUTH_HEADERS)
    resp = reader.post("/tools/forecast_cash", json={"account_id": acct["citizens"], "as_of_date": "2026-10-19",
                                                     "days": 30, "starting_balance": "5116.31", "correlation_id": "r"})
    assert resp.status_code == 200, resp.text


def test_cadences_and_effective_date(seeded):
    client, acct = seeded

    def item(key, cadence, **extra):
        resp = client.post(
            "/tools/upsert_budget_item",
            json={"item_key": key, "name": key, "direction": "outflow", "amount": "10", "cadence": cadence,
                  "bucket": "recurring", "account_id": acct["sfcu"], "effective_date": "2026-11-01",
                  "correlation_id": f"c-{key}", **extra},
        )
        assert resp.status_code == 200, resp.text

    item("m31", "monthly", day_of_month=31)
    item("q", "quarterly", anchor_date="2026-08-31")
    item("a", "annual", anchor_date="2024-02-29")
    item("bw", "biweekly", anchor_date="2026-01-01")  # Thursdays
    out = client.post("/tools/forecast_cash", json={
        "account_id": acct["sfcu"], "as_of_date": "2026-10-19", "days": 160, "starting_balance": "1000",
        "correlation_id": "cad"}).json()
    dates = lambda n: [e["date"] for e in out["events"] if e["name"] == n]
    assert dates("m31") == ["2026-11-30", "2026-12-31", "2027-02-01", "2027-03-01"]  # Jan 31 Sun, Feb 28 Sun, Mar 31 out
    assert dates("q") == ["2026-11-30", "2027-03-01"]
    assert dates("a") == ["2027-03-01"]  # 2027-02-28 is Sunday
    assert dates("bw")[0] == "2026-11-05" and all(
        b > a for a, b in zip(dates("bw"), dates("bw")[1:]))
