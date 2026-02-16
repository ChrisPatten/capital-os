from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from capital_os.api.app import app
from tests.support.auth import AUTH_HEADERS
from capital_os.config import get_settings
from capital_os.db.session import transaction
from capital_os.domain.approval.service import approve_proposed_transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.domain.ledger.service import record_transaction_bundle


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _seed_accounts() -> tuple[str, str]:
    with transaction() as conn:
        debit = create_account(conn, {"code": "1300", "name": "Period Cash", "account_type": "asset"})
        credit = create_account(conn, {"code": "2300", "name": "Period Debt", "account_type": "liability"})
    return debit, credit


def _bundle_payload(debit: str, credit: str, *, external_id: str, amount: str = "250.0000") -> dict:
    return {
        "source_system": "pytest",
        "external_id": external_id,
        "date": "2026-01-15T00:00:00Z",
        "description": "period controlled write",
        "postings": [
            {"account_id": debit, "amount": amount, "currency": "USD"},
            {"account_id": credit, "amount": f"-{amount}", "currency": "USD"},
        ],
        "correlation_id": f"corr-{external_id}",
    }


def test_close_and_lock_period_tools_idempotent(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    close_first = client.post(
        "/tools/close_period",
        json={"period_key": "2026-01", "actor_id": "controller-a", "correlation_id": "corr-close-1"},
    )
    close_second = client.post(
        "/tools/close_period",
        json={"period_key": "2026-01", "actor_id": "controller-a", "correlation_id": "corr-close-2"},
    )
    lock_response = client.post(
        "/tools/lock_period",
        json={"period_key": "2026-01", "actor_id": "controller-a", "correlation_id": "corr-lock-1"},
    )

    assert close_first.status_code == 200
    assert close_first.json()["status"] == "closed"
    assert close_second.status_code == 200
    assert close_second.json()["status"] == "already_closed"
    assert lock_response.status_code == 200
    assert lock_response.json()["status"] == "locked"


def test_closed_period_rejects_non_adjusting_entry_via_api(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    debit, credit = _seed_accounts()
    client.post(
        "/tools/close_period",
        json={"period_key": "2026-01", "actor_id": "controller-a", "correlation_id": "corr-close-api"},
    )

    blocked = client.post(
        "/tools/record_transaction_bundle",
        json=_bundle_payload(debit, credit, external_id="period-closed-api-1"),
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"]["message"] == "period_closed_requires_adjusting_entry"


def test_closed_period_adjusting_entry_requires_approval(db_available, monkeypatch):
    if not db_available:
        pytest.skip("database unavailable")

    monkeypatch.setenv("CAPITAL_OS_APPROVAL_THRESHOLD_AMOUNT", "1000.0000")
    get_settings.cache_clear()

    client = TestClient(app, headers=AUTH_HEADERS)
    debit, credit = _seed_accounts()
    client.post(
        "/tools/close_period",
        json={"period_key": "2026-01", "actor_id": "controller-a", "correlation_id": "corr-close-adjust"},
    )

    proposed = client.post(
        "/tools/record_transaction_bundle",
        json={
            **_bundle_payload(debit, credit, external_id="period-adjusting-1", amount="10.0000"),
            "is_adjusting_entry": True,
            "adjusting_reason_code": "correction",
        },
    )
    assert proposed.status_code == 200
    assert proposed.json()["status"] == "proposed"


def test_locked_period_requires_override(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    client = TestClient(app, headers=AUTH_HEADERS)
    debit, credit = _seed_accounts()
    client.post(
        "/tools/lock_period",
        json={"period_key": "2026-01", "actor_id": "controller-a", "correlation_id": "corr-lock-policy"},
    )

    blocked = client.post(
        "/tools/record_transaction_bundle",
        json=_bundle_payload(debit, credit, external_id="period-lock-1"),
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"]["message"] == "period_locked"


def test_policy_rule_dimensions_and_multi_party_approval(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    debit, credit = _seed_accounts()

    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO policy_rules (
              rule_id, priority, tool_name, entity_id, transaction_category, risk_band,
              threshold_amount, required_approvals, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                "rule-high-risk-1",
                1,
                "record_transaction_bundle",
                "entity-default",
                "tax",
                "high",
                "1.0000",
                2,
            ),
        )

    proposed = record_transaction_bundle(
        {
            **_bundle_payload(debit, credit, external_id="policy-2party-1", amount="5.0000"),
            "transaction_category": "tax",
            "risk_band": "high",
        }
    )

    assert proposed["status"] == "proposed"
    assert proposed["required_approvals"] == 2
    assert proposed["matched_rule_id"] == "rule-high-risk-1"

    first = approve_proposed_transaction(
        {
            "proposal_id": proposed["proposal_id"],
            "approver_id": "approver-a",
            "reason": "first approval",
            "correlation_id": "corr-approve-a",
        }
    )
    assert first["status"] == "proposed"
    assert first["approvals_received"] == 1

    second = approve_proposed_transaction(
        {
            "proposal_id": proposed["proposal_id"],
            "approver_id": "approver-b",
            "reason": "second approval",
            "correlation_id": "corr-approve-b",
        }
    )
    assert second["status"] == "committed"
    assert second["approvals_received"] == 2


def test_multi_party_duplicate_approver_is_deterministic(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    debit, credit = _seed_accounts()
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO policy_rules (
              rule_id, priority, tool_name, threshold_amount, required_approvals, active
            ) VALUES (?, ?, ?, ?, ?, 1)
            """,
            ("rule-dup-approver", 1, "record_transaction_bundle", "1.0000", 2),
        )

    proposed = record_transaction_bundle(_bundle_payload(debit, credit, external_id="policy-dup-1", amount="5.0000"))

    def _approve_once(corr: str) -> dict:
        return approve_proposed_transaction(
            {
                "proposal_id": proposed["proposal_id"],
                "approver_id": "approver-a",
                "reason": "same approver replay",
                "correlation_id": corr,
            }
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(_approve_once, ["corr-dup-a1", "corr-dup-a2"]))

    assert first["status"] == "proposed"
    assert second["status"] == "proposed"
    assert first["output_hash"] == second["output_hash"]

    committed = approve_proposed_transaction(
        {
            "proposal_id": proposed["proposal_id"],
            "approver_id": "approver-b",
            "reason": "complete quorum",
            "correlation_id": "corr-dup-b",
        }
    )
    assert committed["status"] == "committed"


def test_velocity_rule_triggers_policy_gate(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    debit, credit = _seed_accounts()

    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO policy_rules (
              rule_id, priority, tool_name, velocity_limit_count, velocity_window_seconds,
              threshold_amount, required_approvals, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            ("rule-velocity-1", 1, "record_transaction_bundle", 1, 86400, "9999.0000", 1),
        )

    committed = record_transaction_bundle(_bundle_payload(debit, credit, external_id="velocity-committed-1", amount="2.0000"))
    assert committed["status"] == "committed"

    gated = record_transaction_bundle(_bundle_payload(debit, credit, external_id="velocity-proposed-1", amount="2.0000"))
    assert gated["status"] == "proposed"
    assert gated["matched_rule_id"] == "rule-velocity-1"
