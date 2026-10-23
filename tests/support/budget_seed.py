"""Section-6 reference budget (Oct 23, 2026) used by summary and replay tests."""

from __future__ import annotations

from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account

ACCOUNT_SPECS = {
    "citizens": ("1101", "Citizens Checking", "asset"),
    "sfcu": ("1102", "SFCU Checking", "asset"),
    "apple": ("2101", "Apple Card", "liability"),
    "amex": ("2102", "Amex", "liability"),
}


def create_budget_accounts() -> dict[str, str]:
    ids: dict[str, str] = {}
    with transaction() as conn:
        for key, (code, name, kind) in ACCOUNT_SPECS.items():
            ids[key] = create_account(conn, {"code": code, "name": name, "account_type": kind})
    return ids


def reference_items(acct: dict[str, str]) -> list[dict]:
    """(item_key, name, direction, amount, cadence, account, bucket) rows as upsert payloads."""
    items: list[dict] = []

    def inflow(key, name, amount, account):
        items.append(
            dict(item_key=key, name=name, direction="inflow", amount=amount, cadence="biweekly",
                 anchor_date="2026-10-29", account_id=account, effective_date="2026-10-23")
        )

    def outflow(key, name, amount, account, bucket="recurring", cadence="monthly"):
        row = dict(item_key=key, name=name, direction="outflow", amount=amount, cadence=cadence,
                   account_id=account, bucket=bucket, effective_date="2026-10-23")
        if cadence == "monthly":
            row["day_of_month"] = 1
        else:
            row["anchor_date"] = "2026-11-15"
        items.append(row)

    inflow("pay-citizens", "Citizens payroll", "2959.00", acct["citizens"])
    inflow("pay-sfcu", "SFCU payroll", "1341.75", acct["sfcu"])
    inflow("kate-deposit", "Kate deposit", "1511.00", None)

    c = acct["citizens"]
    outflow("life-insurance", "Life insurance", "40.38", c)
    outflow("mortgage", "Mortgage", "3127.46", c)
    outflow("arbella", "Arbella", "276.00", c)
    outflow("discover", "Discover paydown", "590.00", c, bucket="debt")
    outflow("eversource-gas", "Eversource gas", "284.00", c)
    outflow("fios", "Fios", "89.99", c)
    outflow("firstmark", "Firstmark", "520.44", c)
    outflow("apple-card-paydown", "Apple Card paydown", "500.00", c, bucket="debt")
    outflow("highlander", "Highlander", "461.00", c)
    outflow("verizon", "Verizon", "160.73", c)

    s = acct["sfcu"]
    outflow("ohdeer", "OhDeer", "117.00", s)
    outflow("gbh-1", "GBH", "10.00", s)
    outflow("gbh-2", "GBH", "10.00", s)
    outflow("visible", "Visible", "25.00", s)
    outflow("wyze", "Wyze", "11.73", s)
    outflow("electric", "Electric", "265.00", s)
    outflow("water", "Water", "166.00", s)
    outflow("jeep", "Jeep", "543.00", s)
    outflow("train-parking", "Train and parking", "150.00", s)
    outflow("discretionary", "Discretionary", "700.00", s, bucket="discretionary")
    outflow("savings", "Savings", "487.50", s, bucket="savings")

    for i, amt in enumerate(("37.95", "6.06", "5.99", "9.99")):
        outflow(f"apple-sub-{i}", f"Apple Card sub {i}", amt, acct["apple"])
    for i, amt in enumerate(("12.74", "10.00", "10.00", "24.43")):
        outflow(f"amex-sub-{i}", f"Amex sub {i}", amt, acct["amex"])

    for key, name, amt in (
        ("amazon-prime", "Amazon Prime", "139.00"),
        ("excise", "Excise tax", "800.00"),
        ("tax-prep", "Tax prep", "200.00"),
        ("car-maintenance", "Car maintenance", "500.00"),
        ("dog-meds", "Dog meds", "350.00"),
    ):
        outflow(key, name, amt, s, bucket="annual", cadence="annual")
    return items
