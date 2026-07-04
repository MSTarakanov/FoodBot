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
    return PresenceService(
        users,
        "Europe/Belgrade",
        clock=lambda: datetime(2026, 6, 30, 12, 15, tzinfo=ZoneInfo("Europe/Belgrade")),
    )


def create_active_user(users: UserRepository) -> None:
    users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)


def test_meta_requires_registration(users: UserRepository) -> None:
    assert make_presence(users).meta(42, "25") == "Сначала зарегистрируйся: /register"


def test_meta_requires_approved_registration(users: UserRepository) -> None:
    users.create_pending_user(make_profile(), "Максим")

    assert make_presence(users).meta(42, "25") == "Регистрация еще ждет аппрува."


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

    assert make_presence(users).meta(42, "25") == "Регистрация сейчас неактивна."


@pytest.mark.parametrize("raw_minutes", ["abc", "0", "-1", "1441"])
def test_meta_requires_positive_minutes(
    raw_minutes: str,
    users: UserRepository,
) -> None:
    create_active_user(users)

    assert (
        make_presence(users).meta(42, raw_minutes)
        == "Минуты должны быть положительным числом: /meta 25"
    )


def test_meta_uses_display_name_and_fixed_clock(users: UserRepository) -> None:
    create_active_user(users)

    assert make_presence(users).meta(42, "25") == "Максим будет в 12:40"


def test_meta_treats_naive_clock_as_utc(users: UserRepository) -> None:
    create_active_user(users)
    presence = PresenceService(
        users,
        "Europe/Belgrade",
        clock=lambda: datetime(2026, 6, 30, 10, 15),
    )

    assert presence.meta(42, "25") == "Максим будет в 12:40"
