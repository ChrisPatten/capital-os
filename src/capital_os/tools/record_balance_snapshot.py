from __future__ import annotations

from capital_os.domain.ledger.service import record_balance_snapshot
from capital_os.schemas.tools import RecordBalanceSnapshotIn, RecordBalanceSnapshotOut


def handle(payload: dict) -> RecordBalanceSnapshotOut:
    req = RecordBalanceSnapshotIn.model_validate(payload)
    out = record_balance_snapshot(req.model_dump())
    return RecordBalanceSnapshotOut.model_validate(out)
