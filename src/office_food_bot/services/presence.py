from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

from office_food_bot.models import RegisteredUser, UserStatus
from office_food_bot.repositories import UserRepository

_MAX_ETA_MINUTES = 366 * 24 * 60
_SINGLE_ETA_REQUEST_PATTERN = re.compile(r"\s*-?\d+\s*")
_ETA_REQUEST_PATTERN = re.compile(r"\s*(\d+)(?:\s*-\s*(\d+))?\s*")
_MONTH_NAMES = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


@dataclass(frozen=True, slots=True)
class EtaRequest:
    start_minutes: int
    end_minutes: int | None = None


class EtaRequestError(StrEnum):
    INVALID_FORMAT = "invalid_format"
    OUT_OF_RANGE = "out_of_range"
    REVERSED_RANGE = "reversed_range"


@dataclass(frozen=True, slots=True)
class EtaRequestParseResult:
    request: EtaRequest | None = None
    error: EtaRequestError | None = None


@dataclass(frozen=True, slots=True)
class EtaReplySpec:
    single_usage: str
    range_usage: str
    single_today_prefix: Callable[[RegisteredUser], str]
    subject: Callable[[RegisteredUser], str]


class PresenceService:
    def __init__(
        self,
        users: UserRepository,
        timezone_name: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._users = users
        self._timezone = ZoneInfo(timezone_name)
        self._clock = clock or (lambda: datetime.now(tz=UTC))

    def eta(self, telegram_user_id: int, raw_minutes: str, command_name: str) -> str:
        return self._reply_with_eta(
            telegram_user_id,
            raw_minutes,
            _eta_reply_spec(command_name),
        )

    def eta_missing_minutes_reply(self, command_name: str) -> str:
        reply_spec = _eta_reply_spec(command_name)
        return (
            "Напиши через сколько минут или диапазон: "
            f"{reply_spec.single_usage} или {reply_spec.range_usage}"
        )

    def _reply_with_eta(
        self,
        telegram_user_id: int,
        raw_minutes: str,
        reply_spec: EtaReplySpec,
    ) -> str:
        def reply_for_active_user(user: RegisteredUser) -> str:
            parsed_request = _parse_eta_request(raw_minutes)
            if parsed_request.error is not None:
                return _invalid_minutes_reply(reply_spec, parsed_request.error)
            if parsed_request.request is None:
                raise RuntimeError("ETA parser returned neither request nor error.")

            now = self._local_now()
            request = parsed_request.request
            start = self._eta_from(now, request.start_minutes)
            if request.end_minutes is None:
                return _format_single_eta_reply(user, reply_spec, start, now.date())

            end = self._eta_from(now, request.end_minutes)
            return f"{reply_spec.subject(user)} {_format_eta_range(start, end, now.date())}"

        return self._reply_for_active_user(telegram_user_id, reply_for_active_user)

    def _reply_for_active_user(
        self,
        telegram_user_id: int,
        format_reply: Callable[[RegisteredUser], str],
    ) -> str:
        user = self._users.get_by_telegram_id(telegram_user_id)
        if user is None:
            return "Сначала зарегистрируйся: /register"
        if user.status == UserStatus.PENDING:
            return "Регистрация еще ждет аппрува."
        if user.status != UserStatus.ACTIVE:
            return "Регистрация сейчас неактивна."
        return format_reply(user)

    def _local_now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        return now.astimezone(self._timezone)

    def _eta_from(self, now: datetime, minutes: int) -> datetime:
        return now + timedelta(minutes=minutes)


def _parse_eta_request(raw_minutes: str) -> EtaRequestParseResult:
    match = _ETA_REQUEST_PATTERN.fullmatch(raw_minutes)
    if match is None:
        if _SINGLE_ETA_REQUEST_PATTERN.fullmatch(raw_minutes) is not None:
            return EtaRequestParseResult(error=EtaRequestError.OUT_OF_RANGE)
        return EtaRequestParseResult(error=EtaRequestError.INVALID_FORMAT)

    start_minutes = int(match.group(1))
    end_minutes_raw = match.group(2)
    if not _is_valid_eta_minutes(start_minutes):
        return EtaRequestParseResult(error=EtaRequestError.OUT_OF_RANGE)

    if end_minutes_raw is None:
        return EtaRequestParseResult(request=EtaRequest(start_minutes))

    end_minutes = int(end_minutes_raw)
    if not _is_valid_eta_minutes(end_minutes):
        return EtaRequestParseResult(error=EtaRequestError.OUT_OF_RANGE)
    if start_minutes > end_minutes:
        return EtaRequestParseResult(error=EtaRequestError.REVERSED_RANGE)
    return EtaRequestParseResult(request=EtaRequest(start_minutes, end_minutes))


def _is_valid_eta_minutes(minutes: int) -> bool:
    return 0 <= minutes <= _MAX_ETA_MINUTES


def _format_single_eta_reply(
    user: RegisteredUser,
    reply_spec: EtaReplySpec,
    eta: datetime,
    reference_date: date,
) -> str:
    if eta.date() == reference_date:
        return f"{reply_spec.single_today_prefix(user)} {eta:%H:%M}"
    return f"{reply_spec.subject(user)} {_format_single_dated_time(eta, reference_date)}"


def _format_single_dated_time(eta: datetime, reference_date: date) -> str:
    date_label = _date_label(eta, reference_date)
    if date_label is None:
        return f"в {eta:%H:%M}"
    return f"{date_label} в {eta:%H:%M}"


def _format_eta_range(start: datetime, end: datetime, reference_date: date) -> str:
    if start.date() == end.date():
        date_label = _date_label(start, reference_date)
        if date_label is None:
            return f"с {start:%H:%M} до {end:%H:%M}"
        return f"{date_label} с {start:%H:%M} до {end:%H:%M}"

    return (
        f"с {_format_range_endpoint(start, reference_date)} "
        f"до {_format_range_endpoint(end, reference_date)}"
    )


def _format_range_endpoint(moment: datetime, reference_date: date) -> str:
    date_label = _date_label(moment, reference_date)
    if date_label is None:
        return f"{moment:%H:%M}"
    return f"{date_label} {moment:%H:%M}"


def _date_label(moment: datetime, reference_date: date) -> str | None:
    moment_date = moment.date()
    if moment_date == reference_date:
        return None
    if moment_date == reference_date + timedelta(days=1):
        return "завтра"

    month_day = f"{moment.day} {_MONTH_NAMES[moment.month - 1]}"
    if moment.year == reference_date.year:
        return month_day
    return f"{month_day} {moment.year}"


def _meta_single_today_prefix(user: RegisteredUser) -> str:
    return f"{user.display_name} будет в"


def _meta_subject(user: RegisteredUser) -> str:
    return f"{user.display_name} будет"


def _delivery_eta_single_today_prefix(_user: RegisteredUser) -> str:
    return "Ожидаемое время прибытия доставки"


def _delivery_eta_subject(_user: RegisteredUser) -> str:
    return "Ожидаемое время прибытия доставки"


def _invalid_minutes_reply(reply_spec: EtaReplySpec, error: EtaRequestError) -> str:
    if error == EtaRequestError.OUT_OF_RANGE:
        return (
            f"Минуты должны быть от 0 до {_MAX_ETA_MINUTES} (366 дней): "
            f"{reply_spec.single_usage} или {reply_spec.range_usage}"
        )
    if error == EtaRequestError.REVERSED_RANGE:
        return f"Начало диапазона должно быть не больше конца: {reply_spec.range_usage}"

    return (
        "Минуты должны быть числом или диапазоном: "
        f"{reply_spec.single_usage} или {reply_spec.range_usage}"
    )


_META_REPLY_SPEC = EtaReplySpec(
    single_usage="/meta 25",
    range_usage="/meta 20-30",
    single_today_prefix=_meta_single_today_prefix,
    subject=_meta_subject,
)
_DELIVERY_ETA_REPLY_SPEC = EtaReplySpec(
    single_usage="/eta 20",
    range_usage="/eta 20-30",
    single_today_prefix=_delivery_eta_single_today_prefix,
    subject=_delivery_eta_subject,
)
_ETA_REPLY_SPECS = {
    "meta": _META_REPLY_SPEC,
    "eta": _DELIVERY_ETA_REPLY_SPEC,
}


def _eta_reply_spec(command_name: str) -> EtaReplySpec:
    return _ETA_REPLY_SPECS[command_name]
