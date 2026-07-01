from __future__ import annotations

from office_food_bot.database import Database
from office_food_bot.models import TelegramProfile, UserRole, UserStatus
from office_food_bot.repositories import UserRepository


def make_profile(
    telegram_user_id: int = 42,
    username: str | None = "misha",
    first_name: str = "Misha",
    last_name: str | None = None,
) -> TelegramProfile:
    return TelegramProfile(
        telegram_user_id=telegram_user_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
    )


def test_create_pending_user_stores_user_and_telegram_account(
    users: UserRepository,
) -> None:
    user = users.create_pending_user(make_profile(), "Максим")

    assert user.id > 0
    assert user.telegram_user_id == 42
    assert user.display_name == "Максим"
    assert user.status == UserStatus.PENDING
    assert user.role == UserRole.MEMBER
    assert user.username == "misha"
    assert user.first_name == "Misha"
    assert user.last_name is None


def test_get_by_telegram_id_returns_none_for_unknown_user(users: UserRepository) -> None:
    assert users.get_by_telegram_id(404) is None


def test_create_pending_user_returns_existing_user_for_same_telegram_id(
    users: UserRepository,
) -> None:
    created_user = users.create_pending_user(make_profile(), "Максим")
    existing_user = users.create_pending_user(make_profile(username="new"), "Другое")

    assert existing_user.id == created_user.id
    assert existing_user.display_name == "Максим"


def test_refresh_telegram_profile_updates_account(users: UserRepository) -> None:
    users.create_pending_user(make_profile(username="old", first_name="Old"), "Максим")

    users.refresh_telegram_profile(
        make_profile(username="new", first_name="New", last_name="Name")
    )

    user = users.get_by_telegram_id(42)
    assert user is not None
    assert user.username == "new"
    assert user.first_name == "New"
    assert user.last_name == "Name"


def test_approve_by_telegram_id_activates_user(users: UserRepository) -> None:
    users.create_pending_user(make_profile(), "Максим")

    user = users.approve_by_telegram_id(42)

    assert user is not None
    assert user.status == UserStatus.ACTIVE


def test_approve_by_telegram_id_returns_none_for_unknown_user(
    users: UserRepository,
) -> None:
    assert users.approve_by_telegram_id(404) is None


def test_list_pending_users_returns_only_pending_users(users: UserRepository) -> None:
    users.create_pending_user(make_profile(telegram_user_id=42, username="misha"), "Максим")
    users.create_pending_user(make_profile(telegram_user_id=43, username="olya"), "Оля")
    users.approve_by_telegram_id(42)

    pending_users = users.list_pending_users()

    assert [user.telegram_user_id for user in pending_users] == [43]
    assert pending_users[0].display_name == "Оля"


def test_count_splitwise_users_counts_linked_splitwise_users(
    database: Database,
    users: UserRepository,
) -> None:
    user = users.create_pending_user(make_profile(), "Максим")
    assert users.count_splitwise_users() == 0

    with database.connection:
        database.connection.execute(
            """
            INSERT INTO splitwise_users (splitwise_user_id, user_id, display_name)
            VALUES (?, ?, ?)
            """,
            (1001, user.id, "Max Splitwise"),
        )

    assert users.count_splitwise_users() == 1
