from __future__ import annotations

from capital_os.db.session import read_only_connection
from capital_os.domain.ledger.repository import fetch_accounts_for_ids
from capital_os.domain.posture.models import PostureInputSelection, PostureInputs, SelectedAccount


class PostureSelectionError(ValueError):
    pass


ALLOWED_LIQUIDITY_ACCOUNT_TYPES = frozenset({"asset"})


def build_posture_inputs(selection: PostureInputSelection) -> PostureInputs:
    requested_account_ids = selection.liquidity_account_ids
    if len(set(requested_account_ids)) != len(requested_account_ids):
        raise PostureSelectionError("Duplicate liquidity account identifier(s) provided")

    with read_only_connection() as conn:
        rows = fetch_accounts_for_ids(conn, requested_account_ids)

    discovered_account_ids = {row["account_id"] for row in rows}
    missing_account_ids = sorted(set(requested_account_ids) - discovered_account_ids)
    if missing_account_ids:
        raise PostureSelectionError(
            "Unknown liquidity account identifier(s): " + ", ".join(missing_account_ids)
        )

    disallowed = [
        row for row in rows if row["account_type"] not in ALLOWED_LIQUIDITY_ACCOUNT_TYPES
    ]
    if disallowed:
        bad_types = sorted({row["account_type"] for row in disallowed})
        raise PostureSelectionError(
            "Disallowed account type(s) for liquidity selection: " + ", ".join(bad_types)
        )

    selected_accounts = [
        SelectedAccount(
            account_id=row["account_id"],
            code=row["code"],
            name=row["name"],
            account_type=row["account_type"],
        )
        for row in rows
    ]

    ordered_liquidity_ids = [account.account_id for account in selected_accounts]

    return PostureInputs(
        liquidity_account_ids=ordered_liquidity_ids,
        liquidity_accounts=selected_accounts,
        burn_analysis_window=selection.burn_analysis_window,
        reserve_policy=selection.reserve_policy,
        as_of=selection.as_of,
        currency=selection.currency,
    )
