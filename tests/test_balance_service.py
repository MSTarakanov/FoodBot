from __future__ import annotations

from office_food_bot.database import Database
from office_food_bot.models import TelegramProfile
from office_food_bot.repositories import UserRepository
from office_food_bot.services.balances import BalanceService


def make_profile() -> TelegramProfile:
    return TelegramProfile(
        telegram_user_id=42,
        username="misha",
        first_name="Misha",
        last_name=None,
    )


def test_balance_requires_registration(users: UserRepository) -> None:
    assert BalanceService(users).balance(42) == "Сначала зарегистрируйся: /register"


def test_balance_requires_approved_registration(users: UserRepository) -> None:
    users.create_pending_user(make_profile(), "Максим")

    assert BalanceService(users).balance(42) == "Регистрация еще ждет аппрува."


def test_balance_returns_placeholder_when_splitwise_is_empty(
    users: UserRepository,
) -> None:
    users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)

    assert BalanceService(users).balance(42) == "Splitwise пока не подключен."


def test_balance_detects_existing_splitwise_users(
    database: Database,
    users: UserRepository,
) -> None:
    user = users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)
    with database.connection:
        database.connection.execute(
            """
            INSERT INTO splitwise_users (splitwise_user_id, user_id, email)
            VALUES (?, ?, ?)
            """,
            (1001, user.id, "max@example.com"),
        )

    assert BalanceService(users).balance(42) == "Splitwise подключим следующим шагом."
