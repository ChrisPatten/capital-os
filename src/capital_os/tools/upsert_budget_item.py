from __future__ import annotations

from capital_os.domain.budget.service import upsert_budget_item
from capital_os.schemas.tools import UpsertBudgetItemIn, UpsertBudgetItemOut


def handle(payload: dict) -> UpsertBudgetItemOut:
    req = UpsertBudgetItemIn.model_validate(payload)
    out = upsert_budget_item(req.model_dump(mode="python"))
    return UpsertBudgetItemOut.model_validate(out)
