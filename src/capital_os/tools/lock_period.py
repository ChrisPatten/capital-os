from __future__ import annotations

from capital_os.db.session import transaction
from capital_os.domain.periods.service import lock_period
from capital_os.schemas.tools import LockPeriodIn, LockPeriodOut


def handle(payload: dict) -> LockPeriodOut:
    req = LockPeriodIn.model_validate(payload)
    with transaction() as conn:
        out = lock_period(conn, req.model_dump())
    return LockPeriodOut.model_validate(out)
