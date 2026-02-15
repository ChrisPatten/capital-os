from __future__ import annotations

from capital_os.domain.approval.service import approve_proposed_transaction
from capital_os.schemas.tools import ApproveProposedTransactionIn, ApproveProposedTransactionOut



def handle(payload: dict) -> ApproveProposedTransactionOut:
    req = ApproveProposedTransactionIn.model_validate(payload)
    out = approve_proposed_transaction(req.model_dump())
    return ApproveProposedTransactionOut.model_validate(out)
