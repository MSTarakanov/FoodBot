from __future__ import annotations

from office_food_bot.database import Database
from office_food_bot.models import TelegramProfile, UserStatus
from office_food_bot.repositories import UserRepository
from office_food_bot.services.lunch import LunchService


def make_profile() -> TelegramProfile:
    return TelegramProfile(
        telegram_user_id=42,
        username="misha",
        first_name="Misha",
        last_name=None,
    )


def test_lunch_poll_requires_registration(users: UserRepository) -> None:
    assert LunchService(users).poll_block_reason(42) == "Сначала зарегистрируйся: /register"


def test_lunch_poll_requires_approved_registration(users: UserRepository) -> None:
    users.create_pending_user(make_profile(), "Максим")

    assert LunchService(users).poll_block_reason(42) == "Регистрация еще ждет аппрува."


def test_lunch_poll_rejects_inactive_registration(
    database: Database,
    users: UserRepository,
) -> None:
    users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)
    with database.connection:
        database.connection.execute(
            "UPDATE users SET status = ? WHERE display_name = ?",
            (UserStatus.DISABLED.value, "Максим"),
        )

    assert LunchService(users).poll_block_reason(42) == "Регистрация сейчас неактивна."


def test_lunch_poll_allows_active_user(users: UserRepository) -> None:
    users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)

    assert LunchService(users).poll_block_reason(42) is None
