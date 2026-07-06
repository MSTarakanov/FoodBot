from __future__ import annotations

from office_food_bot.database import Database
from office_food_bot.models import TelegramProfile, UserStatus
from office_food_bot.repositories import UserRepository
from office_food_bot.services.lunch import LunchService, lunch_announcement_text


def make_profile(
    telegram_user_id: int = 42,
    username: str | None = "misha",
) -> TelegramProfile:
    return TelegramProfile(
        telegram_user_id=telegram_user_id,
        username=username,
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


def test_lunch_announcement_text_tags_active_users_with_usernames(
    users: UserRepository,
) -> None:
    users.create_pending_user(make_profile(username="misha"), "Максим")
    users.approve_by_telegram_id(42)
    users.create_pending_user(
        make_profile(telegram_user_id=43, username=None),
        "Без Username",
    )
    users.approve_by_telegram_id(43)

    assert lunch_announcement_text(users.list_active_users()) == "Время обедать! @misha"


def test_lunch_announcement_text_skips_users_without_username(
    users: UserRepository,
) -> None:
    users.create_pending_user(make_profile(username=None), "Максим")
    users.approve_by_telegram_id(42)

    assert lunch_announcement_text(users.list_active_users()) == "Время обедать!"
