from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from office_food_bot.database import Database
from office_food_bot.database.database_schema import SCHEMA_SQL
from office_food_bot.database.migrations import load_migrations
from office_food_bot.models import SplitwiseMember, TelegramProfile, UserRole, UserStatus
from office_food_bot.repositories import (
    DebugRepository,
    LunchAutoChatRepository,
    TelegramSeenRepository,
    UserRepository,
    VacationRepository,
)

LEGACY_SCHEMA_SQL = SCHEMA_SQL.replace("email TEXT NOT NULL,", "display_name TEXT NOT NULL,")


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


def test_abandon_by_telegram_id_marks_user_abandoned_and_removes_splitwise(
    users: UserRepository,
) -> None:
    users.save_pending_registration(
        make_profile(),
        "Максим",
        SplitwiseMember(
            splitwise_user_id=1001,
            first_name="Max",
            last_name=None,
            email="max@example.com",
        ),
    )
    users.approve_by_telegram_id(42)

    user = users.abandon_by_telegram_id(42)

    assert user is not None
    assert user.status == UserStatus.ABANDONED
    assert users.list_active_splitwise_users() == ()
    details = users.get_registration_details_by_telegram_id(42)
    assert details is not None
    assert details.splitwise is None


def test_abandon_by_telegram_id_returns_none_for_unknown_user(
    users: UserRepository,
) -> None:
    assert users.abandon_by_telegram_id(404) is None


def test_list_pending_users_returns_only_pending_users(users: UserRepository) -> None:
    users.create_pending_user(make_profile(telegram_user_id=42, username="misha"), "Максим")
    users.create_pending_user(make_profile(telegram_user_id=43, username="olya"), "Оля")
    users.approve_by_telegram_id(42)

    pending_users = users.list_pending_users()

    assert [user.telegram_user_id for user in pending_users] == [43]
    assert pending_users[0].display_name == "Оля"


def test_list_active_users_returns_only_active_users(users: UserRepository) -> None:
    users.create_pending_user(make_profile(telegram_user_id=42, username="misha"), "Максим")
    users.create_pending_user(make_profile(telegram_user_id=43, username="olya"), "Оля")
    users.create_pending_user(make_profile(telegram_user_id=44, username="anton"), "Антон")
    users.approve_by_telegram_id(42)
    users.approve_by_telegram_id(44)

    active_users = users.list_active_users()

    assert [user.username for user in active_users] == ["anton", "misha"]


def test_count_splitwise_users_counts_linked_splitwise_users(
    database: Database,
    users: UserRepository,
) -> None:
    user = users.create_pending_user(make_profile(), "Максим")
    assert users.count_splitwise_users() == 0

    with database.connection:
        database.connection.execute(
            """
            INSERT INTO splitwise_users (splitwise_user_id, user_id, email)
            VALUES (?, ?, ?)
            """,
            (1001, user.id, "max@example.com"),
        )

    assert users.count_splitwise_users() == 1


def test_save_pending_registration_stores_splitwise_member(
    users: UserRepository,
) -> None:
    user = users.save_pending_registration(
        make_profile(),
        "Максим",
        SplitwiseMember(
            splitwise_user_id=1001,
            first_name="Max",
            last_name=None,
            email="max@example.com",
        ),
    )

    pending_registrations = users.list_pending_registrations()

    assert user.display_name == "Максим"
    assert len(pending_registrations) == 1
    assert pending_registrations[0].user.telegram_user_id == 42
    assert pending_registrations[0].splitwise is not None
    assert pending_registrations[0].splitwise.splitwise_user_id == 1001
    assert pending_registrations[0].splitwise.email == "max@example.com"


def test_get_registration_details_by_telegram_id_returns_display_name_and_splitwise(
    users: UserRepository,
) -> None:
    users.save_pending_registration(
        make_profile(),
        "Максим",
        SplitwiseMember(
            splitwise_user_id=1001,
            first_name="Max",
            last_name=None,
            email="max@example.com",
        ),
    )

    details = users.get_registration_details_by_telegram_id(42)

    assert details is not None
    assert details.display_name == "Максим"
    assert details.splitwise is not None
    assert details.splitwise.splitwise_user_id == 1001
    assert details.splitwise.email == "max@example.com"


def test_save_pending_registration_with_skip_removes_existing_splitwise_member(
    users: UserRepository,
) -> None:
    users.save_pending_registration(
        make_profile(),
        "Максим",
        SplitwiseMember(
            splitwise_user_id=1001,
            first_name="Max",
            last_name=None,
            email="max@example.com",
        ),
    )

    users.save_pending_registration(make_profile(), "Максим", None)

    pending_registrations = users.list_pending_registrations()
    assert len(pending_registrations) == 1
    assert pending_registrations[0].splitwise is None


def test_list_active_splitwise_users_returns_only_active_linked_users(
    users: UserRepository,
) -> None:
    users.save_pending_registration(
        make_profile(telegram_user_id=42, username="misha"),
        "Максим",
        SplitwiseMember(
            splitwise_user_id=1001,
            first_name="Max",
            last_name=None,
            email="max@example.com",
        ),
    )
    users.approve_by_telegram_id(42)
    users.save_pending_registration(
        make_profile(telegram_user_id=43, username="pending"),
        "Пендинг",
        SplitwiseMember(
            splitwise_user_id=1002,
            first_name="Pending",
            last_name=None,
            email="pending@example.com",
        ),
    )
    users.create_pending_user(make_profile(telegram_user_id=44, username="unlinked"), "Без Связи")
    users.approve_by_telegram_id(44)

    active_splitwise_users = users.list_active_splitwise_users()

    assert len(active_splitwise_users) == 1
    assert active_splitwise_users[0].display_name == "Максим"
    assert active_splitwise_users[0].splitwise_user_id == 1001
    assert active_splitwise_users[0].email == "max@example.com"


def test_database_init_creates_clean_splitwise_users_schema(tmp_path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.init_schema()
    try:
        columns = [
            str(row["name"])
            for row in database.connection.execute("PRAGMA table_info(splitwise_users)")
        ]
    finally:
        database.close()

    assert columns == ["splitwise_user_id", "user_id", "email", "updated_at"]


def test_database_init_records_schema_migrations(tmp_path) -> None:
    migrations = load_migrations()
    database = Database(tmp_path / "test.sqlite3")
    database.init_schema()
    database.init_schema()
    try:
        columns = [
            str(row["name"])
            for row in database.connection.execute("PRAGMA table_info(schema_migrations)")
        ]
        rows = database.connection.execute(
            """
            SELECT version, name
            FROM schema_migrations
            ORDER BY version
            """,
        ).fetchall()
        schema_version = database.schema_version()
    finally:
        database.close()

    assert columns == ["version", "name", "applied_at"]
    assert [(int(row["version"]), str(row["name"])) for row in rows] == [
        (migration.version, migration.name) for migration in migrations
    ]
    assert schema_version == migrations[-1].version


def test_database_migrations_are_loaded_from_files() -> None:
    assert [(migration.version, migration.name) for migration in load_migrations()] == [
        (1, "initial"),
        (2, "replace_legacy_splitwise_users"),
        (3, "allow_abandoned_user_status"),
    ]


def test_database_init_rejects_unknown_schema_migration(tmp_path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.init_schema()
    with database.connection:
        database.connection.execute(
            "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
            (999, "future_migration"),
        )

    try:
        with pytest.raises(RuntimeError, match="migrations newer than this code: 999"):
            database.init_schema()
    finally:
        database.close()


def test_database_init_creates_telegram_debug_settings_table(tmp_path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.init_schema()
    try:
        columns = [
            str(row["name"])
            for row in database.connection.execute(
                "PRAGMA table_info(telegram_debug_settings)"
            )
        ]
    finally:
        database.close()

    assert columns == ["telegram_user_id", "enabled", "updated_at"]


def test_database_init_creates_telegram_seen_accounts_table(tmp_path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.init_schema()
    try:
        columns = [
            str(row["name"])
            for row in database.connection.execute("PRAGMA table_info(telegram_seen_accounts)")
        ]
    finally:
        database.close()

    assert columns == [
        "telegram_user_id",
        "username",
        "first_name",
        "last_name",
        "first_seen_at",
        "last_seen_at",
    ]


def test_database_init_creates_lunch_auto_chats_table(tmp_path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.init_schema()
    try:
        columns = [
            str(row["name"])
            for row in database.connection.execute("PRAGMA table_info(lunch_auto_chats)")
        ]
    finally:
        database.close()

    assert columns == ["chat_id", "title", "enabled", "created_at", "updated_at"]


def test_database_init_creates_user_vacations_table(tmp_path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.init_schema()
    try:
        columns = [
            str(row["name"])
            for row in database.connection.execute("PRAGMA table_info(user_vacations)")
        ]
    finally:
        database.close()

    assert columns == ["user_id", "until_date", "updated_at"]


def test_database_init_creates_users_status_check_with_abandoned(tmp_path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.init_schema()
    try:
        row = database.connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'",
        ).fetchone()
    finally:
        database.close()

    assert row is not None
    assert "CHECK (status" in str(row["sql"])
    assert "'abandoned'" in str(row["sql"])


def test_database_init_migrates_legacy_users_status_check(tmp_path) -> None:
    database_path = tmp_path / "test.sqlite3"
    legacy_connection = sqlite3.connect(database_path)
    try:
        legacy_connection.executescript(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                display_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'active', 'rejected', 'disabled')),
                role TEXT NOT NULL DEFAULT 'member'
                    CHECK (role IN ('member', 'admin')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE telegram_accounts (
                telegram_user_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            INSERT INTO users (id, display_name, status, role)
            VALUES (1, 'Максим', 'active', 'member');

            INSERT INTO telegram_accounts (
                telegram_user_id,
                user_id,
                username,
                first_name,
                last_name
            )
            VALUES (42, 1, 'misha', 'Misha', NULL);
            """,
        )
    finally:
        legacy_connection.close()

    database = Database(database_path)
    database.init_schema()
    try:
        user = UserRepository(database).abandon_by_telegram_id(42)
        row = database.connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'",
        ).fetchone()
    finally:
        database.close()

    assert user is not None
    assert user.status == UserStatus.ABANDONED
    assert row is not None
    assert "'abandoned'" in str(row["sql"])


def test_lunch_auto_chat_repository_enables_disables_and_lists_chats(
    database: Database,
) -> None:
    chats = LunchAutoChatRepository(database)

    chat = chats.enable(-100, "Office")
    disabled_chat = chats.disable(-100)

    assert chat.chat_id == -100
    assert chat.title == "Office"
    assert chat.enabled
    assert disabled_chat is not None
    assert not disabled_chat.enabled
    assert chats.list_enabled() == ()

    reenabled_chat = chats.enable(-100, "Office 2")

    assert reenabled_chat.title == "Office 2"
    assert reenabled_chat.enabled
    assert [chat.chat_id for chat in chats.list_enabled()] == [-100]


def test_vacation_repository_stores_updates_and_clears_vacation(
    users: UserRepository,
    database: Database,
) -> None:
    user = users.create_pending_user(make_profile(), "Максим")
    vacations = VacationRepository(database)

    vacations.set_until_date(user.id, date(2026, 7, 6))
    vacations.set_until_date(user.id, date(2026, 7, 20))
    vacation = vacations.get(user.id)

    assert vacation is not None
    assert vacation.until_date == date(2026, 7, 20)
    assert vacations.active_user_ids(date(2026, 7, 20)) == frozenset({user.id})
    assert vacations.active_user_ids(date(2026, 7, 21)) == frozenset()

    vacations.clear(user.id)

    assert vacations.get(user.id) is None


def test_debug_repository_persists_debug_status(database: Database) -> None:
    debug = DebugRepository(database)

    assert not debug.is_enabled(7)

    debug.set_enabled(7, True)
    assert DebugRepository(database).is_enabled(7)

    debug.set_enabled(7, False)
    assert not DebugRepository(database).is_enabled(7)


def test_telegram_seen_repository_stores_and_updates_profile(database: Database) -> None:
    seen_accounts = TelegramSeenRepository(database)

    seen_accounts.remember(make_profile(username="old", first_name="Old"))
    seen_accounts.remember(
        make_profile(username="new", first_name="New", last_name="Name"),
    )

    seen_account = seen_accounts.get(42)

    assert seen_account is not None
    assert seen_account.telegram_user_id == 42
    assert seen_account.username == "new"
    assert seen_account.first_name == "New"
    assert seen_account.last_name == "Name"


def test_telegram_seen_repository_lists_only_unregistered_accounts(
    database: Database,
    users: UserRepository,
) -> None:
    seen_accounts = TelegramSeenRepository(database)
    seen_accounts.remember(make_profile(telegram_user_id=42, username="misha"))
    seen_accounts.remember(make_profile(telegram_user_id=43, username="olya"))
    seen_accounts.remember(make_profile(telegram_user_id=44, username="old"))
    users.create_pending_user(make_profile(telegram_user_id=42, username="misha"), "Максим")
    users.create_pending_user(make_profile(telegram_user_id=44, username="old"), "Олег")
    users.abandon_by_telegram_id(44)

    unregistered_accounts = seen_accounts.list_unregistered(limit=10)

    assert {account.telegram_user_id for account in unregistered_accounts} == {43, 44}


def test_database_init_replaces_empty_legacy_splitwise_users_table(tmp_path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    with database.connection:
        database.connection.executescript(LEGACY_SCHEMA_SQL)
    database.close()

    database = Database(tmp_path / "test.sqlite3")
    database.init_schema()
    try:
        columns = [
            str(row["name"])
            for row in database.connection.execute("PRAGMA table_info(splitwise_users)")
        ]
    finally:
        database.close()

    assert columns == ["splitwise_user_id", "user_id", "email", "updated_at"]


def test_database_init_replaces_non_empty_legacy_splitwise_users_table(tmp_path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    with database.connection:
        database.connection.executescript(LEGACY_SCHEMA_SQL)
        database.connection.execute(
            """
            INSERT INTO users (display_name, status, role)
            VALUES (?, ?, ?)
            """,
            ("Максим", UserStatus.PENDING.value, UserRole.MEMBER.value),
        )
        database.connection.execute(
            """
            INSERT INTO splitwise_users (splitwise_user_id, user_id, display_name)
            VALUES (?, ?, ?)
            """,
            (1001, 1, "Max Splitwise"),
        )
    database.close()

    database = Database(tmp_path / "test.sqlite3")
    database.init_schema()
    try:
        row = database.connection.execute(
            """
            SELECT splitwise_user_id, user_id, email
            FROM splitwise_users
            """,
        ).fetchone()
        columns = [
            str(row["name"])
            for row in database.connection.execute("PRAGMA table_info(splitwise_users)")
        ]
    finally:
        database.close()

    assert columns == ["splitwise_user_id", "user_id", "email", "updated_at"]
    assert row is not None
    assert int(row["splitwise_user_id"]) == 1001
    assert int(row["user_id"]) == 1
    assert row["email"] == ""
