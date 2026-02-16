from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import app
from capital_os.db.session import transaction
from tests.support.auth import AUTH_HEADERS


def _valid_payload(correlation_id: str) -> dict:
    return {
        "entity_ids": ["entity-b", "entity-a"],
        "entities": [
            {
                "entity_id": "entity-a",
                "liquidity": "1000.0000",
                "fixed_burn": "100.0000",
                "variable_burn": "50.0000",
                "minimum_reserve": "300.0000",
                "volatility_buffer": "50.0000",
            },
            {
                "entity_id": "entity-b",
                "liquidity": "800.0000",
                "fixed_burn": "80.0000",
                "variable_burn": "40.0000",
                "minimum_reserve": "200.0000",
                "volatility_buffer": "25.0000",
            },
        ],
        "inter_entity_transfers": [
            {
                "transfer_id": "xfer-1",
                "entity_id": "entity-a",
                "counterparty_entity_id": "entity-b",
                "direction": "out",
                "amount": "100.0000",
            },
            {
                "transfer_id": "xfer-1",
                "entity_id": "entity-b",
                "counterparty_entity_id": "entity-a",
                "direction": "in",
                "amount": "100.0000",
            },
        ],
        "correlation_id": correlation_id,
    }


def test_compute_consolidated_posture_is_deterministic_and_transfer_neutral(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    payload = _valid_payload("corr-consolidated-1")

    first = client.post("/tools/compute_consolidated_posture", json=payload)
    second = client.post("/tools/compute_consolidated_posture", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200

    body = first.json()
    assert body["entity_ids"] == ["entity-a", "entity-b"]
    assert body["transfer_pairs"] == [
        {
            "transfer_id": "xfer-1",
            "entity_a_id": "entity-a",
            "entity_b_id": "entity-b",
            "amount": "100.0000",
        }
    ]
    assert body["liquidity"] == "1800.0000"
    assert body["reserve_target"] == "575.0000"
    assert body["reserve_ratio"] == "3.1304"
    assert body["risk_band"] == "stable"

    entities = {entry["entity_id"]: entry for entry in body["entities"]}
    assert entities["entity-a"]["transfer_net"] == "-100.0000"
    assert entities["entity-a"]["transfer_neutral_liquidity"] == "1100.0000"
    assert entities["entity-b"]["transfer_net"] == "100.0000"
    assert entities["entity-b"]["transfer_neutral_liquidity"] == "700.0000"

    assert body["output_hash"] == second.json()["output_hash"]
    assert body == second.json()

    with transaction() as conn:
        rows = conn.execute(
            """
            SELECT correlation_id, status
            FROM event_log
            WHERE tool_name='compute_consolidated_posture'
            ORDER BY created_at
            """
        ).fetchall()
    assert len(rows) == 2
    assert rows[0]["correlation_id"] == "corr-consolidated-1"
    assert rows[0]["status"] == "ok"
    assert rows[1]["status"] == "ok"


def test_compute_consolidated_posture_validation_failure_is_logged(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    bad_payload = _valid_payload("corr-consolidated-bad")
    bad_payload["inter_entity_transfers"] = bad_payload["inter_entity_transfers"][:1]

    response = client.post("/tools/compute_consolidated_posture", json=bad_payload)
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "validation_error"

    with transaction() as conn:
        rows = conn.execute(
            """
            SELECT correlation_id, status, input_hash, output_hash
            FROM event_log
            WHERE tool_name='compute_consolidated_posture'
            ORDER BY created_at
            """
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["correlation_id"] == "corr-consolidated-bad"
    assert rows[0]["status"] == "validation_error"
    assert rows[0]["input_hash"]
    assert rows[0]["output_hash"]


def test_compute_consolidated_posture_does_not_mutate_canonical_ledger_rows(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    payload = _valid_payload("corr-consolidated-no-mutation")

    with transaction() as conn:
        before = {
            "accounts": conn.execute("SELECT COUNT(*) AS c FROM accounts").fetchone()["c"],
            "ledger_transactions": conn.execute("SELECT COUNT(*) AS c FROM ledger_transactions").fetchone()["c"],
            "ledger_postings": conn.execute("SELECT COUNT(*) AS c FROM ledger_postings").fetchone()["c"],
            "balance_snapshots": conn.execute("SELECT COUNT(*) AS c FROM balance_snapshots").fetchone()["c"],
            "obligations": conn.execute("SELECT COUNT(*) AS c FROM obligations").fetchone()["c"],
        }

    response = client.post("/tools/compute_consolidated_posture", json=payload)
    assert response.status_code == 200

    with transaction() as conn:
        after = {
            "accounts": conn.execute("SELECT COUNT(*) AS c FROM accounts").fetchone()["c"],
            "ledger_transactions": conn.execute("SELECT COUNT(*) AS c FROM ledger_transactions").fetchone()["c"],
            "ledger_postings": conn.execute("SELECT COUNT(*) AS c FROM ledger_postings").fetchone()["c"],
            "balance_snapshots": conn.execute("SELECT COUNT(*) AS c FROM balance_snapshots").fetchone()["c"],
            "obligations": conn.execute("SELECT COUNT(*) AS c FROM obligations").fetchone()["c"],
        }

    assert before == after
