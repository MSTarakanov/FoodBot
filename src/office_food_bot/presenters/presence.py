from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import assert_never

from office_food_bot.messaging import TextMessagePayload
from office_food_bot.models import RegisteredUser
from office_food_bot.presence_models import PresenceKind, PresenceReport

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
class PresenceReplySpec:
    single_today_prefix: Callable[[RegisteredUser], str]
    subject: Callable[[RegisteredUser], str]


def render_presence_report(report: PresenceReport) -> TextMessagePayload:
    spec = _reply_spec(report.kind)
    if report.end is None:
        text = _format_single_eta_reply(
            report.user,
            spec,
            report.start,
            report.reference_date,
        )
    else:
        text = (
            f"{spec.subject(report.user)} "
            f"{_format_eta_range(report.start, report.end, report.reference_date)}"
        )
    return TextMessagePayload(text)


def _format_single_eta_reply(
    user: RegisteredUser,
    spec: PresenceReplySpec,
    eta: datetime,
    reference_date: date,
) -> str:
    if eta.date() == reference_date:
        return f"{spec.single_today_prefix(user)} {eta:%H:%M}"
    return f"{spec.subject(user)} {_format_single_dated_time(eta, reference_date)}"


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


def _reply_spec(kind: PresenceKind) -> PresenceReplySpec:
    match kind:
        case PresenceKind.META:
            return PresenceReplySpec(
                single_today_prefix=_meta_single_today_prefix,
                subject=_meta_subject,
            )
        case PresenceKind.DELIVERY_ETA:
            return PresenceReplySpec(
                single_today_prefix=_delivery_eta_single_today_prefix,
                subject=_delivery_eta_subject,
            )
    assert_never(kind)
