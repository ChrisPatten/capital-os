from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


BALANCE_SOURCE_POLICIES = {"ledger_only", "snapshot_only", "best_available"}


def _normalize_balance_source_policy(raw_value: str) -> str:
    value = raw_value.strip().lower()
    if value not in BALANCE_SOURCE_POLICIES:
        raise ValueError(
            "CAPITAL_OS_BALANCE_SOURCE_POLICY must be one of "
            "ledger_only|snapshot_only|best_available"
        )
    return value


@dataclass(frozen=True)
class Settings:
    app_env: str
    db_url: str
    money_precision: int = 4
    approval_threshold_amount: str = "1000.0000"
    balance_source_policy: str = "best_available"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    db_url = os.getenv("CAPITAL_OS_DB_URL")
    if not db_url:
        db_url = "sqlite:///./data/capital_os.db"

    balance_source_policy = _normalize_balance_source_policy(
        os.getenv("CAPITAL_OS_BALANCE_SOURCE_POLICY", "best_available")
    )

    return Settings(
        app_env=os.getenv("APP_ENV", "dev"),
        db_url=db_url,
        approval_threshold_amount=os.getenv("CAPITAL_OS_APPROVAL_THRESHOLD_AMOUNT", "1000.0000"),
        balance_source_policy=balance_source_policy,
    )
