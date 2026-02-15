from __future__ import annotations

from capital_os.db.session import transaction
from capital_os.domain.periods.service import close_period
from capital_os.schemas.tools import ClosePeriodIn, ClosePeriodOut


def handle(payload: dict) -> ClosePeriodOut:
    req = ClosePeriodIn.model_validate(payload)
    with transaction() as conn:
        out = close_period(conn, req.model_dump())
    return ClosePeriodOut.model_validate(out)
