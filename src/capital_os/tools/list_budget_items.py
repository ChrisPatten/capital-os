from __future__ import annotations

from capital_os.domain.budget.service import list_budget_items
from capital_os.schemas.tools import ListBudgetItemsIn, ListBudgetItemsOut


def handle(payload: dict) -> ListBudgetItemsOut:
    req = ListBudgetItemsIn.model_validate(payload)
    out = list_budget_items(req.model_dump(mode="python"))
    return ListBudgetItemsOut.model_validate(out)
