from __future__ import annotations

from office_food_bot.models import TelegramProfile
from office_food_bot.presenters.lunch import lunch_announcement_text
from office_food_bot.repositories import UserRepository


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
