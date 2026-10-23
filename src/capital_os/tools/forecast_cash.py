from __future__ import annotations

from capital_os.domain.forecast.service import forecast_cash
from capital_os.schemas.tools import ForecastCashIn, ForecastCashOut


def handle(payload: dict) -> ForecastCashOut:
    req = ForecastCashIn.model_validate(payload)
    out = forecast_cash(req.model_dump(mode="python"))
    return ForecastCashOut.model_validate(out)
