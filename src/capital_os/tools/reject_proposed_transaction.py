from __future__ import annotations

from capital_os.domain.approval.service import reject_proposed_transaction
from capital_os.schemas.tools import RejectProposedTransactionIn, RejectProposedTransactionOut



def handle(payload: dict) -> RejectProposedTransactionOut:
    req = RejectProposedTransactionIn.model_validate(payload)
    out = reject_proposed_transaction(req.model_dump())
    return RejectProposedTransactionOut.model_validate(out)
