from __future__ import annotations

from capital_os.db.session import transaction
from capital_os.domain.ledger.service import fulfill_obligation as _service_fulfill
from capital_os.schemas.tools import FulfillObligationIn, FulfillObligationOut


def handle(payload: dict) -> FulfillObligationOut:
    req = FulfillObligationIn.model_validate(payload)
    # Normalize fulfilled_at to ISO string before passing to service
    raw = req.model_dump()
    if raw.get("fulfilled_at") is not None:
        raw["fulfilled_at"] = raw["fulfilled_at"].isoformat(timespec="microseconds")
    out = _service_fulfill(raw)
    return FulfillObligationOut.model_validate(out)
