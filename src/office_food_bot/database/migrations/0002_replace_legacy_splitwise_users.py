from __future__ import annotations

import sqlite3

from office_food_bot.database.database_schema import SPLITWISE_USERS_SCHEMA_SQL

EXPECTED_SPLITWISE_USERS_COLUMNS = {
    "splitwise_user_id",
    "user_id",
    "email",
    "updated_at",
}
LEGACY_SPLITWISE_USERS_COLUMNS = {
    "splitwise_user_id",
    "user_id",
    "display_name",
    "updated_at",
}
LEGACY_SPLITWISE_USERS_TABLE = "splitwise_users_legacy_display_name"


def migrate(connection: sqlite3.Connection) -> None:
    column_names = _splitwise_users_column_names(connection)
    if column_names == EXPECTED_SPLITWISE_USERS_COLUMNS:
        return
    if column_names != LEGACY_SPLITWISE_USERS_COLUMNS:
        msg = f"Unexpected splitwise_users schema: {sorted(column_names)}"
        raise RuntimeError(msg)

    with connection:
        connection.execute(f"ALTER TABLE splitwise_users RENAME TO {LEGACY_SPLITWISE_USERS_TABLE}")
        connection.execute(SPLITWISE_USERS_SCHEMA_SQL)
        connection.execute(
            f"""
            INSERT INTO splitwise_users (
                splitwise_user_id,
                user_id,
                email,
                updated_at
            )
            SELECT
                splitwise_user_id,
                user_id,
                '',
                updated_at
            FROM {LEGACY_SPLITWISE_USERS_TABLE}
            """,
        )
        connection.execute(f"DROP TABLE {LEGACY_SPLITWISE_USERS_TABLE}")


def _splitwise_users_column_names(connection: sqlite3.Connection) -> frozenset[str]:
    rows = connection.execute("PRAGMA table_info(splitwise_users)").fetchall()
    return frozenset(str(row["name"]) for row in rows)
