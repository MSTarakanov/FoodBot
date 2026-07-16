from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

from office_food_bot.database import Database
from office_food_bot.features.coffee.repository import CoffeeSessionRepository
from office_food_bot.models import CoffeeSessionStatus, TelegramProfile
from office_food_bot.repositories import UserRepository


def create_user(users: UserRepository, telegram_user_id: int, name: str) -> int:
    user = users.create_pending_user(
        TelegramProfile(telegram_user_id, name.casefold(), name, None),
        name,
    )
    return user.id


def test_coffee_session_persists_participants_and_history(database: Database) -> None:
    users = UserRepository(database)
    maxim_id = create_user(users, 42, "Максим")
    anna_id = create_user(users, 43, "Анна")
    sessions = CoffeeSessionRepository(database)
    scheduled_at = datetime(2026, 7, 7, 14, tzinfo=UTC)

    coffee = sessions.create(-100, maxim_id, scheduled_at)
    assert sessions.list_recoverable() == (coffee,)
    coffee = sessions.activate(coffee.id, 101)
    coffee = sessions.reschedule(coffee.id, anna_id, scheduled_at)
    sessions.leave(coffee.id, maxim_id)
    completed = sessions.mark_terminal(
        coffee.id,
        CoffeeSessionStatus.COMPLETED,
        scheduled_at,
    )

    assert completed.status == CoffeeSessionStatus.COMPLETED
    assert [user.display_name for user in sessions.list_participants(coffee.id)] == ["Анна"]
    assert sessions.get_open_for_chat(-100) is None
    assert sessions.require(coffee.id).message_id == 101


def test_coffee_session_allows_only_one_open_session_per_chat(
    database: Database,
) -> None:
    users = UserRepository(database)
    user_id = create_user(users, 42, "Максим")
    sessions = CoffeeSessionRepository(database)
    scheduled_at = datetime(2026, 7, 7, 14, tzinfo=UTC)
    sessions.create(-100, user_id, scheduled_at)

    with pytest.raises(sqlite3.IntegrityError):
        sessions.create(-100, user_id, scheduled_at)


def test_fresh_database_contains_poll_and_coffee_tables(database: Database) -> None:
    table_names = {
        str(row["name"])
        for row in database.connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }

    assert {
        "polls",
        "poll_selected_options",
        "user_invitation_preferences",
        "coffee_sessions",
        "coffee_session_participants",
    } <= table_names
    assert database.schema_version() == 14
