from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from office_food_bot.commanding.errors.models import (
    CommandInputError,
    CommonError,
    CommonErrorCode,
    InputErrorCode,
)
from office_food_bot.commands.presence import EtaRequestParser
from office_food_bot.database import Database
from office_food_bot.models import TelegramProfile, UserStatus
from office_food_bot.presence_models import PresenceKind
from office_food_bot.presenters.presence import render_presence_report
from office_food_bot.repositories import UserRepository
from office_food_bot.services.presence import PresenceService
from office_food_bot.services.user_access import ActiveUserResolver


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
    request = EtaRequestParser().parse(raw_minutes)
    return render_presence_report(presence.report(42, request, kind)).text


def create_active_user(users: UserRepository) -> None:
    users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)


def test_meta_requires_registration(users: UserRepository) -> None:
    with pytest.raises(CommonError) as error:
        presence_text(make_presence(users), "25", PresenceKind.META)

    assert error.value.code == CommonErrorCode.REGISTRATION_REQUIRED


def test_meta_requires_approved_registration(users: UserRepository) -> None:
    users.create_pending_user(make_profile(), "Максим")

    with pytest.raises(CommonError) as error:
        presence_text(make_presence(users), "25", PresenceKind.META)

    assert error.value.code == CommonErrorCode.REGISTRATION_PENDING


def test_meta_rejects_inactive_registration(
    database: Database,
    users: UserRepository,
) -> None:
    users.create_pending_user(make_profile(), "Максим")
    user = users.get_by_telegram_id(42)
    assert user is not None
    with database.connection:
        database.connection.execute(
            "UPDATE users SET status = ? WHERE id = ?",
            (UserStatus.DISABLED.value, user.id),
        )

    with pytest.raises(CommonError) as error:
        presence_text(make_presence(users), "25", PresenceKind.META)

    assert error.value.code == CommonErrorCode.REGISTRATION_INACTIVE


@pytest.mark.parametrize(
    "raw_minutes",
    ["abc", "20--30", "20-", "1.5"],
)
def test_meta_rejects_invalid_minutes_format(
    raw_minutes: str,
    users: UserRepository,
) -> None:
    create_active_user(users)

    with pytest.raises(CommandInputError) as error:
        presence_text(make_presence(users), raw_minutes, PresenceKind.META)

    assert error.value.code == InputErrorCode.INVALID_FORMAT


@pytest.mark.parametrize("raw_minutes", ["-1", "527041", "9999999999", "0-527041"])
def test_meta_rejects_out_of_range_minutes(
    raw_minutes: str,
    users: UserRepository,
) -> None:
    create_active_user(users)

    with pytest.raises(CommandInputError) as error:
        presence_text(make_presence(users), raw_minutes, PresenceKind.META)

    assert error.value.code == InputErrorCode.OUT_OF_RANGE


def test_meta_rejects_reversed_minutes_range(users: UserRepository) -> None:
    create_active_user(users)

    with pytest.raises(CommandInputError) as error:
        presence_text(make_presence(users), "30-20", PresenceKind.META)

    assert error.value.code == InputErrorCode.REVERSED_RANGE


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


def test_delivery_eta_requires_registration(users: UserRepository) -> None:
    with pytest.raises(CommonError) as error:
        presence_text(make_presence(users), "20", PresenceKind.DELIVERY_ETA)

    assert error.value.code == CommonErrorCode.REGISTRATION_REQUIRED


@pytest.mark.parametrize(
    "raw_minutes",
    ["abc", "20--30", "20-", "1.5"],
)
def test_delivery_eta_rejects_invalid_minutes_format(
    raw_minutes: str,
    users: UserRepository,
) -> None:
    create_active_user(users)

    with pytest.raises(CommandInputError) as error:
        presence_text(make_presence(users), raw_minutes, PresenceKind.DELIVERY_ETA)

    assert error.value.code == InputErrorCode.INVALID_FORMAT


@pytest.mark.parametrize("raw_minutes", ["-1", "527041", "9999999999", "0-527041"])
def test_delivery_eta_rejects_out_of_range_minutes(
    raw_minutes: str,
    users: UserRepository,
) -> None:
    create_active_user(users)

    with pytest.raises(CommandInputError) as error:
        presence_text(make_presence(users), raw_minutes, PresenceKind.DELIVERY_ETA)

    assert error.value.code == InputErrorCode.OUT_OF_RANGE


def test_delivery_eta_rejects_reversed_minutes_range(users: UserRepository) -> None:
    create_active_user(users)

    with pytest.raises(CommandInputError) as error:
        presence_text(make_presence(users), "30-20", PresenceKind.DELIVERY_ETA)

    assert error.value.code == InputErrorCode.REVERSED_RANGE


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
