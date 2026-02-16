import json
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import app
from tests.support.auth import AUTH_HEADERS
from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account


def test_record_balance_snapshot_records_then_updates_single_canonical_row(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    with transaction() as conn:
        account_id = create_account(conn, {"code": "1300", "name": "Snapshot Cash", "account_type": "asset"})

    first_payload = {
        "source_system": "pytest",
        "account_id": account_id,
        "snapshot_date": "2026-01-31",
        "balance": "1500.0000",
        "currency": "USD",
        "source_artifact_id": "artifact-1",
        "correlation_id": "corr-snapshot-1",
    }
    second_payload = {
        **first_payload,
        "balance": "1750.0000",
        "source_artifact_id": "artifact-2",
        "correlation_id": "corr-snapshot-2",
    }

    first = client.post("/tools/record_balance_snapshot", json=first_payload)
    second = client.post("/tools/record_balance_snapshot", json=second_payload)

    assert first.status_code == 200
    assert second.status_code == 200
    first_body = first.json()
    second_body = second.json()

    assert first_body["status"] == "recorded"
    assert second_body["status"] == "updated"
    assert first_body["snapshot_id"] == second_body["snapshot_id"]

    with transaction() as conn:
        row = conn.execute(
            """
            SELECT snapshot_id, balance, source_artifact_id
            FROM balance_snapshots
            WHERE account_id=? AND snapshot_date=?
            """,
            (account_id, "2026-01-31"),
        ).fetchone()
        count = conn.execute("SELECT COUNT(*) AS c FROM balance_snapshots").fetchone()["c"]

    assert count == 1
    assert row["snapshot_id"] == first_body["snapshot_id"]
    assert f"{Decimal(str(row['balance'])):.4f}" == "1750.0000"
    assert row["source_artifact_id"] == "artifact-2"


def test_create_or_update_obligation_creates_then_updates_active_record(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    with transaction() as conn:
        account_id = create_account(conn, {"code": "2300", "name": "Obligation Liability", "account_type": "liability"})

    first_payload = {
        "source_system": "pytest",
        "name": "Vendor Payment",
        "account_id": account_id,
        "cadence": "monthly",
        "expected_amount": "325.0000",
        "variability_flag": False,
        "next_due_date": "2026-02-15",
        "metadata": {"category": "vendor"},
        "correlation_id": "corr-obligation-1",
    }
    second_payload = {
        **first_payload,
        "expected_amount": "400.0000",
        "variability_flag": True,
        "next_due_date": "2026-03-15",
        "metadata": {"category": "vendor", "priority": "high"},
        "correlation_id": "corr-obligation-2",
    }

    first = client.post("/tools/create_or_update_obligation", json=first_payload)
    second = client.post("/tools/create_or_update_obligation", json=second_payload)

    assert first.status_code == 200
    assert second.status_code == 200
    first_body = first.json()
    second_body = second.json()

    assert first_body["status"] == "created"
    assert second_body["status"] == "updated"
    assert first_body["obligation_id"] == second_body["obligation_id"]

    with transaction() as conn:
        row = conn.execute(
            """
            SELECT obligation_id, expected_amount, variability_flag, next_due_date, metadata, active
            FROM obligations
            WHERE source_system=? AND name=? AND account_id=?
            """,
            ("pytest", "Vendor Payment", account_id),
        ).fetchone()
        count = conn.execute("SELECT COUNT(*) AS c FROM obligations").fetchone()["c"]

    assert count == 1
    assert row["obligation_id"] == first_body["obligation_id"]
    assert f"{Decimal(str(row['expected_amount'])):.4f}" == "400.0000"
    assert row["variability_flag"] == 1
    assert row["next_due_date"] == "2026-03-15"
    assert json.loads(row["metadata"]) == {"category": "vendor", "priority": "high"}
    assert row["active"] == 1
