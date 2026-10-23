from __future__ import annotations

import pytest

from capital_os.config import get_settings
from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.domain.ledger.service import record_transaction_bundle


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _configure(monkeypatch, *, enabled: str | None, threshold: str = "1000.0000") -> None:
    monkeypatch.setenv("CAPITAL_OS_APPROVAL_THRESHOLD_AMOUNT", threshold)
    if enabled is None:
        monkeypatch.delenv("CAPITAL_OS_APPROVALS_ENABLED", raising=False)
    else:
        monkeypatch.setenv("CAPITAL_OS_APPROVALS_ENABLED", enabled)
    get_settings.cache_clear()


def _seed_accounts() -> tuple[str, str]:
    with transaction() as conn:
        debit = create_account(conn, {"code": "1100", "name": "Operating Cash", "account_type": "asset"})
        credit = create_account(conn, {"code": "2100", "name": "Operating Debt", "account_type": "liability"})
    return debit, credit


def _payload(debit: str, credit: str, external_id: str, amount: str = "1500.0000") -> dict:
    return {
        "source_system": "pytest",
        "external_id": external_id,
        "date": "2026-01-01T00:00:00Z",
        "description": "flag test transfer",
        "postings": [
            {"account_id": debit, "amount": amount, "currency": "USD"},
            {"account_id": credit, "amount": f"-{amount}", "currency": "USD"},
        ],
        "correlation_id": f"corr-{external_id}",
    }


def _proposal_count() -> int:
    with transaction() as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM approval_proposals").fetchone()["n"]


def test_flag_off_above_threshold_commits_directly(db_available, monkeypatch):
    if not db_available:
        pytest.skip("database unavailable")
    _configure(monkeypatch, enabled="false")
    debit, credit = _seed_accounts()

    result = record_transaction_bundle(_payload(debit, credit, "flag-off-1"))

    assert result["status"] == "committed"
    assert _proposal_count() == 0


def test_flag_off_duplicate_match_still_proposed(db_available, monkeypatch):
    if not db_available:
        pytest.skip("database unavailable")
    _configure(monkeypatch, enabled="false")
    debit, credit = _seed_accounts()

    first = record_transaction_bundle(_payload(debit, credit, "flag-off-dup-1"))
    second = record_transaction_bundle(_payload(debit, credit, "flag-off-dup-2"))

    assert first["status"] == "committed"
    assert second["status"] == "proposed"
    assert _proposal_count() == 1


def test_flag_on_above_threshold_proposed(db_available, monkeypatch):
    if not db_available:
        pytest.skip("database unavailable")
    _configure(monkeypatch, enabled="true")
    debit, credit = _seed_accounts()

    result = record_transaction_bundle(_payload(debit, credit, "flag-on-1"))

    assert result["status"] == "proposed"
    assert _proposal_count() == 1


def test_flag_default_is_true(monkeypatch):
    _configure(monkeypatch, enabled=None)
    assert get_settings().approvals_enabled is True


@pytest.mark.parametrize("raw,expected", [("FALSE", False), ("0", False), ("No", False), ("True", True), ("1", True), ("YES", True)])
def test_flag_parsing(monkeypatch, raw, expected):
    _configure(monkeypatch, enabled=raw)
    assert get_settings().approvals_enabled is expected


def test_flag_invalid_value_raises(monkeypatch):
    monkeypatch.setenv("CAPITAL_OS_APPROVALS_ENABLED", "maybe")
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="CAPITAL_OS_APPROVALS_ENABLED"):
        get_settings()
