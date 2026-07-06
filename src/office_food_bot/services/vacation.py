from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

from office_food_bot.models import RegisteredUser, UserStatus
from office_food_bot.repositories import UserRepository, VacationRepository

MAX_VACATION_DAYS = 366
VACATION_DATE_FORMAT_ERROR_TEXT = (
    "Не понял дату. Напиши количество дней или дату: "
    "/vacation 2, /vacation 20.07, /vacation 2026-07-20"
)
VACATION_OFF_ARGUMENTS = frozenset({"off"})
_DAY_COUNT_PATTERN = re.compile(r"[+-]?\d+")
_ISO_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
_SHORT_DATE_PATTERN = re.compile(r"(\d{1,2})([./])(\d{1,2})(?:\2(\d{4}))?")


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
        users: UserRepository,
        vacations: VacationRepository,
        timezone_name: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._users = users
        self._vacations = vacations
        self._timezone = ZoneInfo(timezone_name)
        self._clock = clock or (lambda: datetime.now(tz=UTC))

    def reply(self, telegram_user_id: int, raw_argument: str) -> str:
        user = self._users.get_by_telegram_id(telegram_user_id)
        if user is None:
            return "Сначала зарегистрируйся: /register"
        if user.status == UserStatus.PENDING:
            return "Регистрация еще ждет аппрува."
        if user.status != UserStatus.ACTIVE:
            return "Регистрация сейчас неактивна."

        today = self._local_today()
        request = parse_vacation_request(raw_argument, today)
        if request.kind == VacationRequestKind.STATUS:
            return self._status_text(user, today)
        if request.kind == VacationRequestKind.CLEAR:
            self._vacations.clear(user.id)
            return f"{user.display_name} больше не в отпуске."
        if request.kind == VacationRequestKind.INVALID:
            return VACATION_DATE_FORMAT_ERROR_TEXT

        if request.until_date is None:
            return VACATION_DATE_FORMAT_ERROR_TEXT

        self._vacations.set_until_date(user.id, request.until_date)
        return f"{user.display_name} в отпуске до {_format_date(request.until_date)}."

    def _status_text(self, user: RegisteredUser, today: date) -> str:
        vacation = self._vacations.get(user.id)
        if vacation is not None and vacation.until_date >= today:
            return f"{user.display_name} в отпуске до {_format_date(vacation.until_date)}."
        return (
            f"{user.display_name} не в отпуске. "
            "Чтобы включить: /vacation 2 или /vacation 20.07"
        )

    def _local_today(self) -> date:
        return self._clock().astimezone(self._timezone).date()


def parse_vacation_request(raw_argument: str, today: date) -> VacationRequest:
    argument = raw_argument.strip()
    if not argument:
        return VacationRequest(VacationRequestKind.STATUS)
    if argument.casefold() in VACATION_OFF_ARGUMENTS:
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


def _format_date(day: date) -> str:
    return day.strftime("%d.%m.%Y")
