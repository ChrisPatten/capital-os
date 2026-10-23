from __future__ import annotations

from capital_os.domain.budget.service import get_budget_summary
from capital_os.schemas.tools import GetBudgetSummaryIn, GetBudgetSummaryOut


def handle(payload: dict) -> GetBudgetSummaryOut:
    req = GetBudgetSummaryIn.model_validate(payload)
    out = get_budget_summary(req.model_dump(mode="python"))
    return GetBudgetSummaryOut.model_validate(out)
