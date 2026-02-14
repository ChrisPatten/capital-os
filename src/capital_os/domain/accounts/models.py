from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Account:
    account_id: str
    code: str
    name: str
    account_type: str
    parent_account_id: str | None
    metadata: dict
    created_at: datetime
