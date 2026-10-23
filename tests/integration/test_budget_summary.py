from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal

import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import app
from tests.support.auth import AUTH_HEADERS
from tests.support.budget_seed import create_budget_accounts, reference_items

Q = Decimal("0.0001")


def _q(v: Decimal) -> Decimal:
    return v.quantize(Q, rounding=ROUND_HALF_EVEN)


@pytest.fixture
def seeded(db_available):
    if not db_available:
        pytest.skip("database unavailable")
    client = TestClient(app, headers=AUTH_HEADERS)
    acct = create_budget_accounts()
    items = reference_items(acct)
    for i, item in enumerate(items):
        resp = client.post("/tools/upsert_budget_item", json={**item, "correlation_id": f"seed-{i}"})
        assert resp.status_code == 200, resp.text
    return client, acct, items


def _summary(client, **extra):
    resp = client.post("/tools/get_budget_summary", json={"correlation_id": "sum-1", **extra})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_reference_budget_summary(seeded):
    client, acct, items = seeded
    out = _summary(client)
    buckets = {b["bucket"]: b for b in out["buckets"]}
    assert [b["bucket"] for b in out["buckets"]] == ["recurring", "debt", "annual", "discretionary", "savings"]
    assert Decimal(buckets["recurring"]["monthly_amount"]) == Decimal("6374.8900")
    assert Decimal(buckets["debt"]["monthly_amount"]) == Decimal("1090.0000")
    assert Decimal(buckets["annual"]["monthly_amount"]) == Decimal("165.7500")
    assert Decimal(buckets["discretionary"]["monthly_amount"]) == Decimal("700.0000")
    assert Decimal(buckets["savings"]["monthly_amount"]) == Decimal("487.5000")
    assert Decimal(out["total_outflows_monthly"]) == Decimal("8818.1400")
    assert Decimal(out["take_home_monthly"]) == Decimal("12592.1250")
    assert Decimal(out["untracked_inflows_monthly"]) == Decimal("3273.8333")
    assert Decimal(out["leftover_monthly"]) == Decimal("500.1517")
    assert out["item_count"] == len(items)

    take_home = Decimal("5811.75") * 26 / 12
    assert Decimal(buckets["recurring"]["pct_of_take_home"]) == _q(Decimal("6374.89") / take_home * 100)
    assert Decimal(buckets["recurring"]["pct_of_take_home"]) == Decimal("50.6260")

    accounts = {a["account_id"]: a for a in out["accounts"]}
    assert [a["account_id"] for a in out["accounts"]] == sorted(accounts)
    citizens = accounts[acct["citizens"]]
    assert Decimal(citizens["inflow_monthly"]) == Decimal("6411.1667")
    assert Decimal(citizens["outflow_monthly"]) == Decimal("6050.0000")
    assert Decimal(citizens["net_monthly"]) == Decimal("361.1667")
    assert len(accounts) == 4  # untracked inflow has no account row


def test_independent_decimal_check_matches_tool(seeded):
    client, _acct, items = seeded
    factor = {"monthly": Decimal(1), "biweekly": Decimal(26) / 12, "annual": Decimal(1) / 12}
    th = sum((Decimal(i["amount"]) * factor[i["cadence"]] for i in items if i["direction"] == "inflow"), Decimal(0))
    out_total = sum((Decimal(i["amount"]) * factor[i["cadence"]] for i in items if i["direction"] == "outflow"), Decimal(0))
    out = _summary(client)
    assert Decimal(out["take_home_monthly"]) == _q(th)
    assert Decimal(out["total_outflows_monthly"]) == _q(out_total)


def test_as_of_date_excludes_future_versions_and_entity_filter(seeded):
    client, _acct, _items = seeded
    before = _summary(client, as_of_date="2026-10-22")
    assert before["item_count"] == 0 and Decimal(before["take_home_monthly"]) == 0
    assert Decimal(before["buckets"][0]["pct_of_take_home"]) == 0
    assert _summary(client, as_of_date="2026-10-23")["item_count"] > 0
    assert _summary(client, entity_id="entity-default")["item_count"] > 0
    assert _summary(client, entity_id="other")["item_count"] == 0


def test_quarterly_and_versioned_amount_used(seeded):
    client, acct, _items = seeded
    resp = client.post(
        "/tools/upsert_budget_item",
        json={"item_key": "q", "name": "Quarterly", "direction": "outflow", "amount": "100.00", "cadence": "quarterly",
              "anchor_date": "2026-11-01", "bucket": "recurring", "effective_date": "2026-10-23",
              "correlation_id": "q1"},
    )
    assert resp.status_code == 200
    out = _summary(client)
    assert Decimal(out["total_outflows_monthly"]) == Decimal("8818.1400") + Decimal("33.3333")
