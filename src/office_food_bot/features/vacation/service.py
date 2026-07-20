from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from typing import Protocol, assert_never
from zoneinfo import ZoneInfo

from office_food_bot.application.users.resolver import ActiveUserResolver
from office_food_bot.boolean_input import parse_toggle
from office_food_bot.features.vacation.models import (
    UserVacation,
    VacationReport,
    VacationReportKind,
)

MAX_VACATION_DAYS = 366
_DAY_COUNT_PATTERN = re.compile(r"[+-]?\d+")
_ISO_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
_SHORT_DATE_PATTERN = re.compile(r"(\d{1,2})([./])(\d{1,2})(?:\2(\d{4}))?")


class VacationStore(Protocol):
    def get(self, user_id: int) -> UserVacation | None: ...

    def set_until_date(self, user_id: int, until_date: date) -> UserVacation: ...

    def clear(self, user_id: int) -> None: ...


class VacationRequestKind(StrEnum):
    STATUS = "status"
    CLEAR = "clear"
    SET = "set"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class VacationRequest:
    kind: VacationRequestKind
    until_date: date | None = None


class VacationService:
    def __init__(
        self,
        active_users: ActiveUserResolver,
        vacations: VacationStore,
        timezone_name: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._active_users = active_users
        self._vacations = vacations
        self._timezone = ZoneInfo(timezone_name)
        self._clock = clock or (lambda: datetime.now(tz=UTC))

    def execute(
        self,
        telegram_user_id: int,
        request: VacationRequest,
    ) -> VacationReport:
        user = self._active_users.require_active(telegram_user_id)
        today = self.local_today()
        match request.kind:
            case VacationRequestKind.STATUS:
                vacation = self._vacations.get(user.id)
                if vacation is not None and vacation.until_date >= today:
                    return VacationReport(
                        VacationReportKind.STATUS_ACTIVE,
                        user.display_name,
                        vacation.until_date,
                    )
                return VacationReport(
                    VacationReportKind.STATUS_INACTIVE,
                    user.display_name,
                )
            case VacationRequestKind.CLEAR:
                self._vacations.clear(user.id)
                return VacationReport(VacationReportKind.CLEARED, user.display_name)
            case VacationRequestKind.SET:
                if request.until_date is None:
                    raise RuntimeError("Vacation set request has no end date")
                self._vacations.set_until_date(user.id, request.until_date)
                return VacationReport(
                    VacationReportKind.SET,
                    user.display_name,
                    request.until_date,
                )
            case VacationRequestKind.INVALID:
                raise RuntimeError("Invalid vacation request reached service")
        assert_never(request.kind)

    def local_today(self) -> date:
        return self._clock().astimezone(self._timezone).date()


def parse_vacation_request(raw_argument: str, today: date) -> VacationRequest:
    argument = raw_argument.strip()
    if not argument:
        return VacationRequest(VacationRequestKind.STATUS)
    if parse_toggle(argument) is False:
        return VacationRequest(VacationRequestKind.CLEAR)
    if _DAY_COUNT_PATTERN.fullmatch(argument):
        return _parse_day_count(argument, today)

    parsed_date = _parse_date_argument(argument, today)
    if parsed_date is None:
        return VacationRequest(VacationRequestKind.INVALID)
    if parsed_date < today or _days_until(parsed_date, today) > MAX_VACATION_DAYS:
        return VacationRequest(VacationRequestKind.INVALID)
    return VacationRequest(VacationRequestKind.SET, parsed_date)


def _parse_day_count(argument: str, today: date) -> VacationRequest:
    day_count = int(argument)
    if day_count == 0:
        return VacationRequest(VacationRequestKind.CLEAR)
    if day_count < 0 or day_count > MAX_VACATION_DAYS:
        return VacationRequest(VacationRequestKind.INVALID)
    return VacationRequest(VacationRequestKind.SET, today + timedelta(days=day_count - 1))


def _parse_date_argument(argument: str, today: date) -> date | None:
    if _ISO_DATE_PATTERN.fullmatch(argument):
        return _parse_iso_date(argument)

    match = _SHORT_DATE_PATTERN.fullmatch(argument)
    if match is None:
        return None

    day = int(match.group(1))
    month = int(match.group(3))
    year_text = match.group(4)
    if year_text is not None:
        return _date_or_none(int(year_text), month, day)

    candidate = _date_or_none(today.year, month, day)
    if candidate is None:
        return None
    if candidate < today:
        return _date_or_none(today.year + 1, month, day)
    return candidate


def _parse_iso_date(argument: str) -> date | None:
    try:
        return date.fromisoformat(argument)
    except ValueError:
        return None


def _date_or_none(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _days_until(until_date: date, today: date) -> int:
    return (until_date - today).days
