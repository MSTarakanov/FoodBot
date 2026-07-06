from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from office_food_bot.database import Database
from office_food_bot.models import TelegramProfile, UserStatus
from office_food_bot.repositories import UserRepository
from office_food_bot.services.presence import PresenceService


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
        users,
        "Europe/Belgrade",
        clock=lambda: now,
    )


def create_active_user(users: UserRepository) -> None:
    users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)


def test_meta_requires_registration(users: UserRepository) -> None:
    assert make_presence(users).eta(42, "25", "meta") == "Сначала зарегистрируйся: /register"


def test_meta_requires_approved_registration(users: UserRepository) -> None:
    users.create_pending_user(make_profile(), "Максим")

    assert make_presence(users).eta(42, "25", "meta") == "Регистрация еще ждет аппрува."


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

    assert make_presence(users).eta(42, "25", "meta") == "Регистрация сейчас неактивна."


@pytest.mark.parametrize(
    "raw_minutes",
    ["abc", "20--30", "20-", "1.5"],
)
def test_meta_rejects_invalid_minutes_format(
    raw_minutes: str,
    users: UserRepository,
) -> None:
    create_active_user(users)

    assert (
        make_presence(users).eta(42, raw_minutes, "meta")
        == "Минуты должны быть числом или диапазоном: /meta 25 или /meta 20-30"
    )


@pytest.mark.parametrize("raw_minutes", ["-1", "527041", "9999999999", "0-527041"])
def test_meta_rejects_out_of_range_minutes(
    raw_minutes: str,
    users: UserRepository,
) -> None:
    create_active_user(users)

    assert (
        make_presence(users).eta(42, raw_minutes, "meta")
        == "Минуты должны быть от 0 до 527040 (366 дней): /meta 25 или /meta 20-30"
    )


def test_meta_rejects_reversed_minutes_range(users: UserRepository) -> None:
    create_active_user(users)

    assert (
        make_presence(users).eta(42, "30-20", "meta")
        == "Начало диапазона должно быть не больше конца: /meta 20-30"
    )


def test_meta_uses_display_name_and_fixed_clock(users: UserRepository) -> None:
    create_active_user(users)

    assert make_presence(users).eta(42, "25", "meta") == "Максим будет в 12:40"


def test_meta_allows_zero_minutes(users: UserRepository) -> None:
    create_active_user(users)

    assert make_presence(users).eta(42, "0", "meta") == "Максим будет в 12:15"


def test_meta_formats_tomorrow_eta(users: UserRepository) -> None:
    create_active_user(users)
    presence = make_presence_at(
        users,
        datetime(2026, 6, 30, 23, 50, tzinfo=ZoneInfo("Europe/Belgrade")),
    )

    assert presence.eta(42, "20", "meta") == "Максим будет завтра в 00:10"


def test_meta_formats_current_year_date_eta(users: UserRepository) -> None:
    create_active_user(users)

    assert make_presence(users).eta(42, "2880", "meta") == "Максим будет 2 июля в 12:15"


def test_meta_formats_next_year_date_eta(users: UserRepository) -> None:
    create_active_user(users)
    presence = make_presence_at(
        users,
        datetime(2026, 12, 30, 12, 15, tzinfo=ZoneInfo("Europe/Belgrade")),
    )

    assert presence.eta(42, "2880", "meta") == "Максим будет 1 января 2027 в 12:15"


def test_meta_formats_today_range(users: UserRepository) -> None:
    create_active_user(users)

    assert make_presence(users).eta(42, "25-35", "meta") == "Максим будет с 12:40 до 12:50"


def test_meta_formats_zero_range_from_current_time(users: UserRepository) -> None:
    create_active_user(users)

    assert make_presence(users).eta(42, "0-10", "meta") == "Максим будет с 12:15 до 12:25"


def test_meta_formats_tomorrow_range(users: UserRepository) -> None:
    create_active_user(users)
    presence = make_presence_at(
        users,
        datetime(2026, 6, 30, 23, 0, tzinfo=ZoneInfo("Europe/Belgrade")),
    )

    assert presence.eta(42, "65-75", "meta") == "Максим будет завтра с 00:05 до 00:15"


def test_meta_formats_cross_day_range(users: UserRepository) -> None:
    create_active_user(users)
    presence = make_presence_at(
        users,
        datetime(2026, 7, 6, 13, 5, tzinfo=ZoneInfo("Europe/Belgrade")),
    )

    assert presence.eta(42, "1500-3001", "meta") == (
        "Максим будет с завтра 14:05 до 8 июля 15:06"
    )


def test_delivery_eta_requires_registration(users: UserRepository) -> None:
    assert make_presence(users).eta(42, "20", "eta") == "Сначала зарегистрируйся: /register"


@pytest.mark.parametrize(
    "raw_minutes",
    ["abc", "20--30", "20-", "1.5"],
)
def test_delivery_eta_rejects_invalid_minutes_format(
    raw_minutes: str,
    users: UserRepository,
) -> None:
    create_active_user(users)

    assert (
        make_presence(users).eta(42, raw_minutes, "eta")
        == "Минуты должны быть числом или диапазоном: /eta 20 или /eta 20-30"
    )


@pytest.mark.parametrize("raw_minutes", ["-1", "527041", "9999999999", "0-527041"])
def test_delivery_eta_rejects_out_of_range_minutes(
    raw_minutes: str,
    users: UserRepository,
) -> None:
    create_active_user(users)

    assert (
        make_presence(users).eta(42, raw_minutes, "eta")
        == "Минуты должны быть от 0 до 527040 (366 дней): /eta 20 или /eta 20-30"
    )


def test_delivery_eta_rejects_reversed_minutes_range(users: UserRepository) -> None:
    create_active_user(users)

    assert (
        make_presence(users).eta(42, "30-20", "eta")
        == "Начало диапазона должно быть не больше конца: /eta 20-30"
    )


def test_delivery_eta_uses_fixed_clock(users: UserRepository) -> None:
    create_active_user(users)

    assert (
        make_presence(users).eta(42, "20", "eta")
        == "Ожидаемое время прибытия доставки 12:35"
    )


def test_delivery_eta_formats_range(users: UserRepository) -> None:
    create_active_user(users)

    assert make_presence(users).eta(42, "20 - 30", "eta") == (
        "Ожидаемое время прибытия доставки с 12:35 до 12:45"
    )


def test_meta_treats_naive_clock_as_utc(users: UserRepository) -> None:
    create_active_user(users)
    presence = PresenceService(
        users,
        "Europe/Belgrade",
        clock=lambda: datetime(2026, 6, 30, 10, 15),
    )

    assert presence.eta(42, "25", "meta") == "Максим будет в 12:40"
