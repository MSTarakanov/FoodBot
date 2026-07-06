from __future__ import annotations

from datetime import date

import holidays


class BusinessCalendarService:
    def __init__(self, country_code: str = "RS") -> None:
        self._holidays = holidays.country_holidays(country_code)

    def is_working_day(self, day: date) -> bool:
        return bool(self._holidays.is_working_day(day))
