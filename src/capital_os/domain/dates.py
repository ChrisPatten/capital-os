"""Pure, clock-free date helpers shared by domain services."""

from __future__ import annotations

import calendar
from datetime import date, timedelta


def add_months(d: date, months: int, day: int | None = None) -> date:
    """Add ``months`` to ``d``; target day is ``day`` or ``d.day``, clamped to month end."""
    index = d.year * 12 + (d.month - 1) + months
    year, month0 = divmod(index, 12)
    month = month0 + 1
    target_day = day if day is not None else d.day
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(target_day, last_day))


def next_business_day(d: date) -> date:
    """Saturday/Sunday move to the following Monday; weekdays unchanged. No holidays."""
    weekday = d.weekday()
    if weekday == 5:
        return d + timedelta(days=2)
    if weekday == 6:
        return d + timedelta(days=1)
    return d
