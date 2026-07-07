from __future__ import annotations

import sqlite3

from office_food_bot.database.database_schema import USERS_SCHEMA_SQL


def migrate(connection: sqlite3.Connection) -> None:
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
