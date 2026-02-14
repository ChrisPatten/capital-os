from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    app_env: str
    db_url: str
    money_precision: int = 4


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    db_url = os.getenv("CAPITAL_OS_DB_URL")
    if not db_url:
        db_url = "sqlite:///./data/capital_os.db"

    return Settings(app_env=os.getenv("APP_ENV", "dev"), db_url=db_url)
