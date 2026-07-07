from __future__ import annotations

import sqlite3

from office_food_bot.database.database_schema import (
    SCHEMA_SQL,
    SPLITWISE_USERS_SCHEMA_SQL,
    USERS_SCHEMA_SQL,
)
from office_food_bot.database.migrations.runner import Migration

EXPECTED_SPLITWISE_USERS_COLUMNS = {
    "splitwise_user_id",
    "user_id",
    "email",
    "updated_at",
}


def create_current_schema(connection: sqlite3.Connection) -> None:
    with connection:
        connection.executescript(SCHEMA_SQL)


def recreate_empty_legacy_splitwise_users(connection: sqlite3.Connection) -> None:
    column_rows = connection.execute("PRAGMA table_info(splitwise_users)").fetchall()
    column_names = {str(row["name"]) for row in column_rows}
    if column_names == EXPECTED_SPLITWISE_USERS_COLUMNS:
        return

    row = connection.execute("SELECT COUNT(*) FROM splitwise_users").fetchone()
    row_count = 0 if row is None else int(row[0])
    if row_count > 0:
        msg = (
            "splitwise_users has legacy rows. Refusing to recreate it automatically "
            "because that would lose Splitwise links."
        )
        raise RuntimeError(msg)

    with connection:
        connection.execute("DROP TABLE splitwise_users")
        connection.execute(SPLITWISE_USERS_SCHEMA_SQL)


def allow_abandoned_user_status(connection: sqlite3.Connection) -> None:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'",
    ).fetchone()
    if row is None or "'abandoned'" in str(row["sql"]):
        return

    connection.commit()
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute("PRAGMA legacy_alter_table = ON")
    try:
        connection.execute("BEGIN")
        connection.execute("ALTER TABLE users RENAME TO users_legacy_status_check")
        connection.execute(USERS_SCHEMA_SQL)
        connection.execute(
            """
            INSERT INTO users (
                id,
                display_name,
                status,
                role,
                created_at,
                updated_at
            )
            SELECT
                id,
                display_name,
                status,
                role,
                created_at,
                updated_at
            FROM users_legacy_status_check
            """,
        )
        connection.execute("DROP TABLE users_legacy_status_check")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.execute("PRAGMA legacy_alter_table = OFF")
        connection.execute("PRAGMA foreign_keys = ON")

    broken_references = connection.execute("PRAGMA foreign_key_check").fetchall()
    if broken_references:
        msg = "users status schema migration left broken foreign keys"
        raise RuntimeError(msg)


MIGRATIONS = (
    Migration(1, "create_current_schema", create_current_schema),
    Migration(2, "recreate_empty_legacy_splitwise_users", recreate_empty_legacy_splitwise_users),
    Migration(3, "allow_abandoned_user_status", allow_abandoned_user_status),
)
