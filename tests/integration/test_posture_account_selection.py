from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from capital_os.db.session import transaction
from capital_os.domain.ledger.repository import create_account
from capital_os.domain.posture.models import BurnAnalysisWindow, PostureInputSelection, ReservePolicyParameters
from capital_os.domain.posture.service import PostureSelectionError, build_posture_inputs
from capital_os.observability.hashing import canonical_json, payload_hash


def _selection(account_ids: list[str]) -> PostureInputSelection:
    return PostureInputSelection(
        liquidity_account_ids=account_ids,
        burn_analysis_window=BurnAnalysisWindow(
            window_start=datetime(2026, 1, 1, tzinfo=UTC),
            window_end=datetime(2026, 1, 31, tzinfo=UTC),
        ),
        reserve_policy=ReservePolicyParameters(
            minimum_reserve_usd=Decimal("1000.00"),
            volatility_buffer_usd=Decimal("25.00"),
        ),
        as_of=datetime(2026, 2, 1, tzinfo=UTC),
        currency="USD",
    )


def test_build_posture_inputs_orders_accounts_deterministically(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    with transaction() as conn:
        cash = create_account(conn, {"code": "1100", "name": "Cash", "account_type": "asset"})
        checking = create_account(conn, {"code": "1000", "name": "Checking", "account_type": "asset"})

    inputs = build_posture_inputs(_selection([cash, checking]))

    assert [account.code for account in inputs.liquidity_accounts] == ["1000", "1100"]
    assert inputs.liquidity_account_ids == [checking, cash]


def test_build_posture_inputs_is_byte_stable_for_same_state_and_config(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    with transaction() as conn:
        first = create_account(conn, {"code": "1100", "name": "Cash", "account_type": "asset"})
        second = create_account(conn, {"code": "1000", "name": "Checking", "account_type": "asset"})

    selection = _selection([first, second])
    output_one = build_posture_inputs(selection).model_dump()
    output_two = build_posture_inputs(selection).model_dump()

    assert canonical_json(output_one) == canonical_json(output_two)
    assert payload_hash(output_one) == payload_hash(output_two)


def test_build_posture_inputs_rejects_unknown_account(db_available):
    if not db_available:
        pytest.skip("database unavailable")

    with pytest.raises(PostureSelectionError):
        build_posture_inputs(_selection(["missing-account-id"]))


@pytest.mark.parametrize("account_type", ["income", "liability", "equity", "expense"])
def test_build_posture_inputs_rejects_disallowed_account_type(db_available, account_type: str):
    if not db_available:
        pytest.skip("database unavailable")

    with transaction() as conn:
        non_liquidity = create_account(
            conn,
            {"code": "4000", "name": "Non-Liquidity", "account_type": account_type},
        )

    with pytest.raises(PostureSelectionError):
        build_posture_inputs(_selection([non_liquidity]))
