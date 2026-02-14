from __future__ import annotations

from capital_os.domain.ledger.service import create_or_update_obligation
from capital_os.schemas.tools import CreateOrUpdateObligationIn, CreateOrUpdateObligationOut


def handle(payload: dict) -> CreateOrUpdateObligationOut:
    req = CreateOrUpdateObligationIn.model_validate(payload)
    out = create_or_update_obligation(req.model_dump())
    return CreateOrUpdateObligationOut.model_validate(out)
