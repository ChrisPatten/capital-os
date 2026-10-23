import random
from decimal import Decimal

import pytest

from capital_os.config import get_settings
from capital_os.db.session import transaction
from capital_os.domain.approval.service import approve_proposed_transaction, reject_proposed_transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.domain.ledger.service import record_transaction_bundle
from capital_os.tools.close_period import handle as close_period_tool
from capital_os.tools.lock_period import handle as lock_period_tool
from capital_os.tools.analyze_debt import handle as analyze_debt_tool
from capital_os.tools.compute_consolidated_posture import handle as compute_consolidated_posture_tool
from capital_os.tools.compute_capital_posture import handle as compute_capital_posture_tool
from capital_os.tools.simulate_spend import handle as simulate_spend_tool


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_output_hash_reproducible_for_same_input(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    with transaction() as conn:
        a1 = create_account(conn, {"code": "1000", "name": "Cash", "account_type": "asset"})
        a2 = create_account(conn, {"code": "9100", "name": "Owner Equity", "account_type": "equity"})

    payload = {
        "source_system": "pytest",
        "external_id": "replay-1",
        "date": "2026-01-01T00:00:00Z",
        "description": "owner seed",
        "postings": [
            {"account_id": a1, "amount": "100.00", "currency": "USD"},
            {"account_id": a2, "amount": "-100.00", "currency": "USD"},
        ],
        "correlation_id": "corr-replay",
    }

    first = record_transaction_bundle(payload)
    second = record_transaction_bundle(payload)
    assert first["output_hash"] == second["output_hash"]


def test_seeded_repeat_runs_keep_posture_output_hash_stable(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    for seed in range(1, 21):
        rng = random.Random(seed)
        payload = {
            "liquidity": f"{Decimal(rng.randint(10_000, 100_000)):.4f}",
            "fixed_burn": f"{Decimal(rng.randint(2_000, 20_000)):.4f}",
            "variable_burn": f"{Decimal(rng.randint(500, 7_000)):.4f}",
            "minimum_reserve": f"{Decimal(rng.randint(5_000, 60_000)):.4f}",
            "volatility_buffer": f"{Decimal(rng.randint(0, 5_000)):.4f}",
            "correlation_id": f"corr-posture-seed-{seed}",
        }

        first = compute_capital_posture_tool(payload).model_dump(mode="json")
        second = compute_capital_posture_tool(payload).model_dump(mode="json")

        assert first["output_hash"] == second["output_hash"]
        assert first == second


def test_consolidated_posture_output_hash_is_reproducible(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    payload = {
        "entity_ids": ["entity-b", "entity-a"],
        "entities": [
            {
                "entity_id": "entity-a",
                "liquidity": "12000.0000",
                "fixed_burn": "3000.0000",
                "variable_burn": "900.0000",
                "minimum_reserve": "6000.0000",
                "volatility_buffer": "700.0000",
            },
            {
                "entity_id": "entity-b",
                "liquidity": "9000.0000",
                "fixed_burn": "2000.0000",
                "variable_burn": "800.0000",
                "minimum_reserve": "5000.0000",
                "volatility_buffer": "600.0000",
            },
        ],
        "inter_entity_transfers": [
            {
                "transfer_id": "seed-xfer-1",
                "entity_id": "entity-a",
                "counterparty_entity_id": "entity-b",
                "direction": "out",
                "amount": "1500.0000",
            },
            {
                "transfer_id": "seed-xfer-1",
                "entity_id": "entity-b",
                "counterparty_entity_id": "entity-a",
                "direction": "in",
                "amount": "1500.0000",
            },
        ],
        "correlation_id": "corr-consolidated-replay",
    }

    first = compute_consolidated_posture_tool(payload).model_dump(mode="json")
    second = compute_consolidated_posture_tool(payload).model_dump(mode="json")

    assert first["output_hash"] == second["output_hash"]
    assert first == second


def test_seeded_repeat_runs_keep_simulation_output_hash_stable(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    for seed in range(1, 21):
        rng = random.Random(seed)
        one_time_amount = Decimal(rng.randint(50, 800))
        recurring_amount = Decimal(rng.randint(20, 250))
        horizon = rng.randint(2, 6)
        occurrences = rng.randint(2, 6)

        payload = {
            "starting_liquidity": f"{Decimal(rng.randint(1_000, 20_000)):.4f}",
            "start_date": "2026-01-01",
            "horizon_periods": horizon,
            "spends": [
                {
                    "spend_id": f"one-time-{seed}",
                    "amount": f"{one_time_amount:.4f}",
                    "type": "one_time",
                    "spend_date": "2026-01-10",
                },
                {
                    "spend_id": f"recurring-{seed}",
                    "amount": f"{recurring_amount:.4f}",
                    "type": "recurring",
                    "start_date": "2026-01-05",
                    "cadence": "weekly",
                    "occurrences": occurrences,
                },
            ],
            "correlation_id": f"corr-sim-seed-{seed}",
        }

        first = simulate_spend_tool(payload).model_dump(mode="json")
        second = simulate_spend_tool(payload).model_dump(mode="json")

        assert first["output_hash"] == second["output_hash"]
        assert first == second


def test_seeded_repeat_runs_keep_debt_output_hash_stable(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    for seed in range(1, 21):
        rng = random.Random(seed)
        payload = {
            "liabilities": [
                {
                    "liability_id": f"loan-{seed}-a",
                    "current_balance": f"{Decimal(rng.randint(2_000, 12_000)):.4f}",
                    "apr": f"{Decimal(rng.randint(300, 2500)) / Decimal('100'):.4f}",
                    "minimum_payment": f"{Decimal(rng.randint(50, 400)):.4f}",
                },
                {
                    "liability_id": f"loan-{seed}-b",
                    "current_balance": f"{Decimal(rng.randint(1_500, 20_000)):.4f}",
                    "apr": f"{Decimal(rng.randint(100, 2200)) / Decimal('100'):.4f}",
                    "minimum_payment": f"{Decimal(rng.randint(40, 500)):.4f}",
                },
            ],
            "optional_payoff_amount": f"{Decimal(rng.randint(0, 4_000)):.4f}",
            "reserve_floor": f"{Decimal(rng.randint(0, 3_500)):.4f}",
            "correlation_id": f"corr-debt-seed-{seed}",
        }

        first = analyze_debt_tool(payload).model_dump(mode="json")
        second = analyze_debt_tool(payload).model_dump(mode="json")

        assert first["output_hash"] == second["output_hash"]
        assert first == second


def test_approval_tools_output_hash_reproducible_on_replay(db_available, monkeypatch):
    if not db_available:
        pytest.skip("database unavailable")

    monkeypatch.setenv("CAPITAL_OS_APPROVAL_THRESHOLD_AMOUNT", "100.0000")
    get_settings.cache_clear()

    with transaction() as conn:
        debit = create_account(conn, {"code": "1200", "name": "Replay Cash", "account_type": "asset"})
        credit = create_account(conn, {"code": "2200", "name": "Replay Debt", "account_type": "liability"})

    proposed = record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "approval-replay-1",
            "date": "2026-01-01T00:00:00Z",
            "description": "approval replay",
            "postings": [
                {"account_id": debit, "amount": "250.0000", "currency": "USD"},
                {"account_id": credit, "amount": "-250.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-approval-proposed",
        }
    )
    assert proposed["status"] == "proposed"

    first_approve = approve_proposed_transaction(
        {
            "proposal_id": proposed["proposal_id"],
            "reason": "approved",
            "correlation_id": "corr-approval-approve-1",
        }
    )
    second_approve = approve_proposed_transaction(
        {
            "proposal_id": proposed["proposal_id"],
            "reason": "approved replay",
            "correlation_id": "corr-approval-approve-2",
        }
    )

    assert first_approve["output_hash"] == second_approve["output_hash"]
    assert first_approve == second_approve

    proposed_reject = record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "approval-replay-2",
            "date": "2026-01-01T00:00:00Z",
            "description": "approval reject replay",
            "postings": [
                {"account_id": debit, "amount": "180.0000", "currency": "USD"},
                {"account_id": credit, "amount": "-180.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-approval-proposed-reject",
        }
    )
    assert proposed_reject["status"] == "proposed"

    first_reject = reject_proposed_transaction(
        {
            "proposal_id": proposed_reject["proposal_id"],
            "reason": "not aligned",
            "correlation_id": "corr-approval-reject-1",
        }
    )
    second_reject = reject_proposed_transaction(
        {
            "proposal_id": proposed_reject["proposal_id"],
            "reason": "ignored in replay",
            "correlation_id": "corr-approval-reject-2",
        }
    )

    assert first_reject["output_hash"] == second_reject["output_hash"]
    assert first_reject == second_reject


def test_period_tools_output_hash_reproducible_on_replay(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    payload = {"period_key": "2026-03", "actor_id": "controller-a", "correlation_id": "corr-close-replay"}
    first_close = close_period_tool(payload).model_dump(mode="json")
    second_close = close_period_tool(payload).model_dump(mode="json")

    assert first_close["output_hash"] != second_close["output_hash"]
    assert second_close["status"] == "already_closed"

    lock_payload = {"period_key": "2026-03", "actor_id": "controller-a", "correlation_id": "corr-lock-replay"}
    first_lock = lock_period_tool(lock_payload).model_dump(mode="json")
    second_lock = lock_period_tool(lock_payload).model_dump(mode="json")

    assert first_lock["status"] == "locked"
    assert second_lock["status"] == "already_locked"
    assert first_lock["state"] == second_lock["state"] == "locked"


def test_duplicate_risk_proposal_output_hash_reproducible_on_replay(db_available, monkeypatch):
    if not db_available:
        pytest.skip("database unavailable")

    monkeypatch.setenv("CAPITAL_OS_APPROVAL_THRESHOLD_AMOUNT", "1000.0000")
    get_settings.cache_clear()

    with transaction() as conn:
        debit = create_account(conn, {"code": "1000", "name": "Replay Dup Debit", "account_type": "asset"})
        credit = create_account(conn, {"code": "2000", "name": "Replay Dup Credit", "account_type": "liability"})

    record_transaction_bundle(
        {
            "source_system": "pytest",
            "external_id": "dup-replay-seed",
            "date": "2026-04-01T00:00:00Z",
            "description": "seed duplicate replay",
            "postings": [
                {"account_id": debit, "amount": "75.0000", "currency": "USD"},
                {"account_id": credit, "amount": "-75.0000", "currency": "USD"},
            ],
            "correlation_id": "corr-dup-replay-seed",
        }
    )

    payload = {
        "source_system": "pytest",
        "external_id": "dup-replay-candidate",
        "date": "2026-04-01T10:30:00Z",
        "description": "duplicate replay candidate",
        "postings": [
            {"account_id": debit, "amount": "75.00004", "currency": "USD"},
            {"account_id": credit, "amount": "-75.0000", "currency": "USD"},
        ],
        "correlation_id": "corr-dup-replay-candidate-1",
    }
    first = record_transaction_bundle(payload)
    second = record_transaction_bundle({**payload, "correlation_id": "corr-dup-replay-candidate-2"})

    assert first["status"] == "proposed"
    assert second["status"] == "proposed"
    assert first["output_hash"] == second["output_hash"]
    assert first["proposed_transaction"] == second["proposed_transaction"]
    assert first["matched_transactions"] == second["matched_transactions"]


def test_recurring_obligation_fulfill_and_list_hashes_reproducible(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    from datetime import date

    from capital_os.domain.ledger.service import create_or_update_obligation, fulfill_obligation
    from capital_os.tools.list_obligations import handle as list_obligations_tool

    with transaction() as conn:
        account_id = create_account(conn, {"code": "2399", "name": "Replay Obligation", "account_type": "liability"})
    created = create_or_update_obligation(
        {
            "source_system": "pytest",
            "name": "Replay Mortgage",
            "account_id": account_id,
            "cadence": "monthly",
            "expected_amount": Decimal("3127.4600"),
            "variability_flag": False,
            "next_due_date": date(2026, 11, 3),
            "metadata": {},
            "active": True,
            "entity_id": "entity-default",
            "recurrence": "monthly",
            "day_of_month": 3,
            "funding_account_id": account_id,
            "bucket": "recurring",
            "correlation_id": "replay-create",
        }
    )
    fulfill_payload = {
        "obligation_id": created["obligation_id"],
        "fulfilled_by_transaction_id": "txn-1",
        "fulfilled_at": "2026-11-03T00:00:00.000000+00:00",
        "expected_due_date": date(2026, 11, 3),
        "correlation_id": "replay-fulfill",
    }
    first = fulfill_obligation(dict(fulfill_payload))
    assert first["status"] == "fulfilled"
    assert first["next_due_date"] == "2026-12-03"

    # Replaying with the guard is a no-op with a reproducible output_hash.
    replay_a = fulfill_obligation(dict(fulfill_payload))
    replay_b = fulfill_obligation(dict(fulfill_payload))
    assert replay_a["status"] == "already_fulfilled"
    assert replay_a["output_hash"] == replay_b["output_hash"]

    list_a = list_obligations_tool({"correlation_id": "replay-list"}).model_dump(mode="json")
    list_b = list_obligations_tool({"correlation_id": "replay-list"}).model_dump(mode="json")
    assert list_a["obligations"][0]["recurrence"] == "monthly"
    assert list_a["obligations"][0]["next_due_date"] == "2026-12-03"
    assert list_a["output_hash"] == list_b["output_hash"]


def test_budget_summary_and_list_hashes_reproducible_and_order_independent(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    import random

    from capital_os.domain.budget.service import (
        get_budget_summary,
        list_budget_items,
        upsert_budget_item,
    )
    from tests.support.budget_seed import create_budget_accounts, reference_items

    acct = create_budget_accounts()
    items = reference_items(acct)
    shuffled = list(items)
    random.Random(7).shuffle(shuffled)
    for i, item in enumerate(shuffled):
        upsert_budget_item({**item, "entity_id": "entity-default", "correlation_id": f"replay-seed-{i}"})

    summary_a = get_budget_summary({"correlation_id": "replay-sum"})
    summary_b = get_budget_summary({"correlation_id": "replay-sum"})
    assert summary_a == summary_b
    assert summary_a["output_hash"] == summary_b["output_hash"]

    list_a = list_budget_items({"correlation_id": "replay-list", "limit": 500})
    list_b = list_budget_items({"correlation_id": "replay-list", "limit": 500})
    assert list_a["output_hash"] == list_b["output_hash"]
    assert [i["item_key"] for i in list_a["items"]] == sorted(i["item_key"] for i in items)

    # Seed the same budget into a second entity in a different order and with different
    # item_keys/item_ids: per-entity summaries must hash identically (no ids or timestamps leak in).
    with transaction() as conn:
        conn.execute(
            "INSERT INTO entities (entity_id, code, name, metadata) VALUES ('entity-b','B','Entity B','{}')"
        )
    reordered = list(items)
    random.Random(99).shuffle(reordered)
    for i, item in enumerate(reordered):
        upsert_budget_item(
            {**item, "item_key": f"b-{item['item_key']}", "entity_id": "entity-b", "correlation_id": f"replay-b-{i}"}
        )
    summary_default = get_budget_summary({"correlation_id": "replay-ent", "entity_id": "entity-default"})
    summary_b = get_budget_summary({"correlation_id": "replay-ent", "entity_id": "entity-b"})
    assert summary_default["item_count"] == summary_b["item_count"] == len(items)
    assert summary_default["output_hash"] == summary_b["output_hash"]
