from __future__ import annotations

from capital_os.domain.ledger.service import record_transaction_bundle
from capital_os.schemas.tools import RecordTransactionBundleIn, RecordTransactionBundleOut


def handle(payload: dict) -> RecordTransactionBundleOut:
    req = RecordTransactionBundleIn.model_validate(payload)
    out = record_transaction_bundle(req.model_dump())
    return RecordTransactionBundleOut.model_validate(out)
