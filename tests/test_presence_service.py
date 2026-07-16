from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from office_food_bot.application.users.models import TelegramProfile
from office_food_bot.application.users.resolver import ActiveUserResolver
from office_food_bot.commanding.errors.models import (
    InputErrorCode,
)
from office_food_bot.commands.presence import EtaRequestParser, EtaRequestResolver
from office_food_bot.features.presence.models import EtaRequest, PresenceKind
from office_food_bot.features.presence.rendering import render_presence_report
from office_food_bot.features.presence.service import PresenceService
from office_food_bot.infrastructure.persistence.users import UserRepository
from office_food_bot.result import Result


def make_profile() -> TelegramProfile:
    return TelegramProfile(
        telegram_user_id=42,
        username="misha",
        first_name="Misha",
        last_name=None,
    )


def make_presence(users: UserRepository) -> PresenceService:
    return make_presence_at(
        users,
        datetime(2026, 6, 30, 12, 15, tzinfo=ZoneInfo("Europe/Belgrade")),
    )


def make_presence_at(users: UserRepository, now: datetime) -> PresenceService:
    return PresenceService(
        ActiveUserResolver(users),
        "Europe/Belgrade",
        clock=lambda: now,
    )


def presence_text(
    presence: PresenceService,
    raw_minutes: str,
    kind: PresenceKind,
) -> str:
    request = parsed_eta(raw_minutes)
    return render_presence_report(presence.report(42, request, kind)).text


def parsed_eta(raw_minutes: str) -> EtaRequest:
    return EtaRequestResolver().resolve(EtaRequestParser().parse(raw_minutes)).fold(
        lambda request: request,
        lambda code: pytest.fail(f"Unexpected ETA parse error: {code}"),
    )


def eta_parse_error(raw_minutes: str) -> InputErrorCode:
    result: Result[EtaRequest, InputErrorCode] = EtaRequestResolver().resolve(
        EtaRequestParser().parse(raw_minutes)
    )
    return result.fold(
        lambda request: pytest.fail(f"Unexpected ETA request: {request}"),
        lambda code: code,
    )


def create_active_user(users: UserRepository) -> None:
    users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)


@pytest.mark.parametrize(
    "raw_minutes",
    ["abc", "20--30", "20-", "1.5"],
)
def test_meta_rejects_invalid_minutes_format(
    raw_minutes: str,
    users: UserRepository,
) -> None:
    assert eta_parse_error(raw_minutes) == InputErrorCode.INVALID_FORMAT


@pytest.mark.parametrize("raw_minutes", ["-1", "527041", "9999999999", "0-527041"])
def test_meta_rejects_out_of_range_minutes(
    raw_minutes: str,
    users: UserRepository,
) -> None:
    assert eta_parse_error(raw_minutes) == InputErrorCode.OUT_OF_RANGE


def test_meta_rejects_reversed_minutes_range(users: UserRepository) -> None:
    assert eta_parse_error("30-20") == InputErrorCode.REVERSED_RANGE


def test_meta_uses_display_name_and_fixed_clock(users: UserRepository) -> None:
    create_active_user(users)

    assert presence_text(make_presence(users), "25", PresenceKind.META) == (
        "Максим будет в 12:40"
    )


def test_meta_allows_zero_minutes(users: UserRepository) -> None:
    create_active_user(users)

    assert presence_text(make_presence(users), "0", PresenceKind.META) == (
        "Максим будет в 12:15"
    )


def test_meta_formats_tomorrow_eta(users: UserRepository) -> None:
    create_active_user(users)
    presence = make_presence_at(
        users,
        datetime(2026, 6, 30, 23, 50, tzinfo=ZoneInfo("Europe/Belgrade")),
    )

    assert presence_text(presence, "20", PresenceKind.META) == (
        "Максим будет завтра в 00:10"
    )


def test_meta_formats_current_year_date_eta(users: UserRepository) -> None:
    create_active_user(users)

    assert presence_text(make_presence(users), "2880", PresenceKind.META) == (
        "Максим будет 2 июля в 12:15"
    )


def test_meta_formats_next_year_date_eta(users: UserRepository) -> None:
    create_active_user(users)
    presence = make_presence_at(
        users,
        datetime(2026, 12, 30, 12, 15, tzinfo=ZoneInfo("Europe/Belgrade")),
    )

    assert presence_text(presence, "2880", PresenceKind.META) == (
        "Максим будет 1 января 2027 в 12:15"
    )


def test_meta_formats_today_range(users: UserRepository) -> None:
    create_active_user(users)

    assert presence_text(make_presence(users), "25-35", PresenceKind.META) == (
        "Максим будет с 12:40 до 12:50"
    )


def test_meta_formats_zero_range_from_current_time(users: UserRepository) -> None:
    create_active_user(users)

    assert presence_text(make_presence(users), "0-10", PresenceKind.META) == (
        "Максим будет с 12:15 до 12:25"
    )


def test_meta_formats_tomorrow_range(users: UserRepository) -> None:
    create_active_user(users)
    presence = make_presence_at(
        users,
        datetime(2026, 6, 30, 23, 0, tzinfo=ZoneInfo("Europe/Belgrade")),
    )

    assert presence_text(presence, "65-75", PresenceKind.META) == (
        "Максим будет завтра с 00:05 до 00:15"
    )


def test_meta_formats_cross_day_range(users: UserRepository) -> None:
    create_active_user(users)
    presence = make_presence_at(
        users,
        datetime(2026, 7, 6, 13, 5, tzinfo=ZoneInfo("Europe/Belgrade")),
    )

    assert presence_text(presence, "1500-3001", PresenceKind.META) == (
        "Максим будет с завтра 14:05 до 8 июля 15:06"
    )


@pytest.mark.parametrize(
    "raw_minutes",
    ["abc", "20--30", "20-", "1.5"],
)
def test_delivery_eta_rejects_invalid_minutes_format(
    raw_minutes: str,
    users: UserRepository,
) -> None:
    assert eta_parse_error(raw_minutes) == InputErrorCode.INVALID_FORMAT


@pytest.mark.parametrize("raw_minutes", ["-1", "527041", "9999999999", "0-527041"])
def test_delivery_eta_rejects_out_of_range_minutes(
    raw_minutes: str,
    users: UserRepository,
) -> None:
    assert eta_parse_error(raw_minutes) == InputErrorCode.OUT_OF_RANGE


def test_delivery_eta_rejects_reversed_minutes_range(users: UserRepository) -> None:
    assert eta_parse_error("30-20") == InputErrorCode.REVERSED_RANGE


def test_delivery_eta_uses_fixed_clock(users: UserRepository) -> None:
    create_active_user(users)

    assert presence_text(make_presence(users), "20", PresenceKind.DELIVERY_ETA) == (
        "Ожидаемое время прибытия доставки 12:35"
    )


def test_delivery_eta_formats_range(users: UserRepository) -> None:
    create_active_user(users)

    assert presence_text(make_presence(users), "20 - 30", PresenceKind.DELIVERY_ETA) == (
        "Ожидаемое время прибытия доставки с 12:35 до 12:45"
    )


def test_meta_treats_naive_clock_as_utc(users: UserRepository) -> None:
    create_active_user(users)
    presence = PresenceService(
        ActiveUserResolver(users),
        "Europe/Belgrade",
        clock=lambda: datetime(2026, 6, 30, 10, 15),
    )

    assert presence_text(presence, "25", PresenceKind.META) == "Максим будет в 12:40"
