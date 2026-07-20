from __future__ import annotations

from datetime import date

from office_food_bot.features.lunch.calendar import BusinessCalendarService


def test_serbia_calendar_allows_regular_workday() -> None:
    calendar = BusinessCalendarService()

    assert calendar.is_working_day(date(2026, 6, 30))


def test_serbia_calendar_rejects_weekend() -> None:
    calendar = BusinessCalendarService()

    assert not calendar.is_working_day(date(2026, 7, 4))


def test_serbia_calendar_rejects_public_holiday() -> None:
    calendar = BusinessCalendarService()

    assert not calendar.is_working_day(date(2026, 1, 1))
