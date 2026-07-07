from __future__ import annotations

import sqlite3

from office_food_bot.database.database_schema import SPLITWISE_USERS_SCHEMA_SQL

EXPECTED_SPLITWISE_USERS_COLUMNS = {
    "splitwise_user_id",
    "user_id",
    "email",
    "updated_at",
}


def migrate(connection: sqlite3.Connection) -> None:
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
