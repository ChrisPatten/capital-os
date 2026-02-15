from __future__ import annotations

from capital_os.domain.debt.engine import DebtAnalysisInputs, analyze_liabilities_with_hash


def analyze_debt(payload: dict) -> dict:
    inputs = DebtAnalysisInputs.model_validate(payload)
    return analyze_liabilities_with_hash(inputs)
