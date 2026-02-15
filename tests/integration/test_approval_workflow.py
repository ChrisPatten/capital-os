from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from capital_os.config import get_settings
from capital_os.db.session import transaction
from capital_os.domain.approval.service import approve_proposed_transaction, reject_proposed_transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.domain.ledger.service import record_transaction_bundle


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _seed_accounts() -> tuple[str, str]:
    with transaction() as conn:
        debit_account = create_account(conn, {"code": "1100", "name": "Operating Cash", "account_type": "asset"})
        credit_account = create_account(conn, {"code": "2100", "name": "Operating Debt", "account_type": "liability"})
    return debit_account, credit_account


def _proposal_payload(debit_account: str, credit_account: str, external_id: str) -> dict:
    return {
        "source_system": "pytest",
        "external_id": external_id,
        "date": "2026-01-01T00:00:00Z",
        "description": "approval-gated transfer",
        "postings": [
            {"account_id": debit_account, "amount": "250.0000", "currency": "USD"},
            {"account_id": credit_account, "amount": "-250.0000", "currency": "USD"},
        ],
        "correlation_id": "corr-proposal",
    }


def _configure_threshold(monkeypatch, threshold: str) -> None:
    monkeypatch.setenv("CAPITAL_OS_APPROVAL_THRESHOLD_AMOUNT", threshold)
    get_settings.cache_clear()


def test_above_threshold_returns_proposed_without_ledger_mutation(db_available, monkeypatch):
    if not db_available:
        pytest.skip("database unavailable")

    _configure_threshold(monkeypatch, "100.0000")
    debit_account, credit_account = _seed_accounts()

    result = record_transaction_bundle(_proposal_payload(debit_account, credit_account, external_id="approval-1"))

    assert result["status"] == "proposed"
    assert result["proposal_id"]
    assert result["impact_amount"] == "250.0000"
    assert result["approval_threshold_amount"] == "100.0000"

    with transaction() as conn:
        tx_count = conn.execute("SELECT COUNT(*) AS c FROM ledger_transactions").fetchone()["c"]
        posting_count = conn.execute("SELECT COUNT(*) AS c FROM ledger_postings").fetchone()["c"]
        proposal_count = conn.execute("SELECT COUNT(*) AS c FROM approval_proposals").fetchone()["c"]

    assert tx_count == 0
    assert posting_count == 0
    assert proposal_count == 1


def test_approve_proposal_commits_once_and_replays_deterministically(db_available, monkeypatch):
    if not db_available:
        pytest.skip("database unavailable")

    _configure_threshold(monkeypatch, "100.0000")
    debit_account, credit_account = _seed_accounts()
    proposed = record_transaction_bundle(_proposal_payload(debit_account, credit_account, external_id="approval-2"))

    def _approve(correlation_suffix: int) -> dict:
        return approve_proposed_transaction(
            {
                "proposal_id": proposed["proposal_id"],
                "reason": "approved",
                "correlation_id": f"corr-approve-{correlation_suffix}",
            }
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(_approve, [1, 2, 3, 4]))

    transaction_ids = {row["transaction_id"] for row in results}
    output_hashes = {row["output_hash"] for row in results}

    assert len(transaction_ids) == 1
    assert len(output_hashes) == 1
    assert all(row["status"] == "committed" for row in results)

    with transaction() as conn:
        tx_count = conn.execute("SELECT COUNT(*) AS c FROM ledger_transactions").fetchone()["c"]
        proposal = conn.execute(
            "SELECT status, approved_transaction_id FROM approval_proposals WHERE proposal_id=?",
            (proposed["proposal_id"],),
        ).fetchone()

    assert tx_count == 1
    assert proposal["status"] == "committed"
    assert proposal["approved_transaction_id"] in transaction_ids


def test_duplicate_above_threshold_requests_replay_canonical_proposal(db_available, monkeypatch):
    if not db_available:
        pytest.skip("database unavailable")

    _configure_threshold(monkeypatch, "100.0000")
    debit_account, credit_account = _seed_accounts()
    payload = _proposal_payload(debit_account, credit_account, external_id="approval-dup-proposal")

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(record_transaction_bundle, [payload, payload]))

    assert first["status"] == "proposed"
    assert second["status"] == "proposed"
    assert first["proposal_id"] == second["proposal_id"]
    assert first["output_hash"] == second["output_hash"]

    with transaction() as conn:
        proposal_count = conn.execute("SELECT COUNT(*) AS c FROM approval_proposals").fetchone()["c"]
        tx_count = conn.execute("SELECT COUNT(*) AS c FROM ledger_transactions").fetchone()["c"]

    assert proposal_count == 1
    assert tx_count == 0


def test_reject_proposal_is_idempotent_and_non_mutating(db_available, monkeypatch):
    if not db_available:
        pytest.skip("database unavailable")

    _configure_threshold(monkeypatch, "100.0000")
    debit_account, credit_account = _seed_accounts()
    proposed = record_transaction_bundle(_proposal_payload(debit_account, credit_account, external_id="approval-3"))

    first = reject_proposed_transaction(
        {
            "proposal_id": proposed["proposal_id"],
            "reason": "insufficient documentation",
            "correlation_id": "corr-reject-1",
        }
    )
    second = reject_proposed_transaction(
        {
            "proposal_id": proposed["proposal_id"],
            "reason": "ignored for replay",
            "correlation_id": "corr-reject-2",
        }
    )

    assert first["status"] == "rejected"
    assert second["status"] == "rejected"
    assert first["proposal_id"] == second["proposal_id"]
    assert first["output_hash"] == second["output_hash"]

    with transaction() as conn:
        tx_count = conn.execute("SELECT COUNT(*) AS c FROM ledger_transactions").fetchone()["c"]
        proposal = conn.execute(
            "SELECT status FROM approval_proposals WHERE proposal_id=?",
            (proposed["proposal_id"],),
        ).fetchone()

    assert tx_count == 0
    assert proposal["status"] == "rejected"


def test_approval_write_rolls_back_when_event_log_fails(db_available, monkeypatch):
    if not db_available:
        pytest.skip("database unavailable")

    _configure_threshold(monkeypatch, "100.0000")
    debit_account, credit_account = _seed_accounts()
    proposed = record_transaction_bundle(_proposal_payload(debit_account, credit_account, external_id="approval-4"))

    with transaction() as conn:
        conn.execute(
            """
            CREATE TRIGGER fail_approve_event_log
            BEFORE INSERT ON event_log
            FOR EACH ROW
            WHEN NEW.tool_name='approve_proposed_transaction'
            BEGIN
              SELECT RAISE(ABORT, 'forced event log failure');
            END;
            """
        )

    with pytest.raises(Exception):
        approve_proposed_transaction(
            {
                "proposal_id": proposed["proposal_id"],
                "reason": "approve with forced event failure",
                "correlation_id": "corr-approve-fail",
            }
        )

    with transaction() as conn:
        conn.execute("DROP TRIGGER IF EXISTS fail_approve_event_log")
        tx_count = conn.execute("SELECT COUNT(*) AS c FROM ledger_transactions").fetchone()["c"]
        proposal_status = conn.execute(
            "SELECT status FROM approval_proposals WHERE proposal_id=?",
            (proposed["proposal_id"],),
        ).fetchone()["status"]

    assert tx_count == 0
    assert proposal_status == "proposed"
