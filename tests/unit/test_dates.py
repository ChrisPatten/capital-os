from datetime import date

from capital_os.domain.dates import add_months, next_business_day


def test_add_months_clamps_to_month_end():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2028, 1, 31), 1) == date(2028, 2, 29)
    assert add_months(date(2026, 3, 31), 1) == date(2026, 4, 30)


def test_add_months_day_override_restores_original_day():
    assert add_months(date(2026, 2, 28), 1, day=31) == date(2026, 3, 31)
    assert add_months(date(2026, 3, 31), 1, day=31) == date(2026, 4, 30)
    assert add_months(date(2026, 11, 3), 1, day=3) == date(2026, 12, 3)


def test_add_months_quarter_and_year_rollover():
    assert add_months(date(2026, 11, 15), 3) == date(2027, 2, 15)
    assert add_months(date(2026, 12, 1), 1) == date(2027, 1, 1)
    assert add_months(date(2026, 1, 1), -1) == date(2025, 12, 1)


def test_add_months_annual_from_leap_day():
    assert add_months(date(2028, 2, 29), 12) == date(2029, 2, 28)
    assert add_months(date(2028, 2, 29), 48) == date(2032, 2, 29)


def test_next_business_day():
    assert next_business_day(date(2026, 10, 24)) == date(2026, 10, 26)  # Saturday
    assert next_business_day(date(2026, 10, 25)) == date(2026, 10, 26)  # Sunday
    assert next_business_day(date(2026, 10, 26)) == date(2026, 10, 26)  # Monday
    assert next_business_day(date(2026, 10, 30)) == date(2026, 10, 30)  # Friday
