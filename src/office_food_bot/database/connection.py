from __future__ import annotations

import sqlite3
from pathlib import Path

from office_food_bot.database.database_schema import (
    SCHEMA_SQL,
    SPLITWISE_USERS_SCHEMA_SQL,
    USERS_SCHEMA_SQL,
)

EXPECTED_SPLITWISE_USERS_COLUMNS = {
    "splitwise_user_id",
    "user_id",
    "email",
    "updated_at",
}


class Database:
    def __init__(self, path: Path) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")

    @property
    def connection(self) -> sqlite3.Connection:
        return self._connection

    def init_schema(self) -> None:
        with self._connection:
            self._connection.executescript(SCHEMA_SQL)
        self._ensure_users_status_schema()
        with self._connection:
            self._ensure_splitwise_users_schema()

    def close(self) -> None:
        self._connection.close()

    def _ensure_users_status_schema(self) -> None:
        row = self._connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'",
        ).fetchone()
        if row is None or "'abandoned'" in str(row["sql"]):
            return

        self._connection.commit()
        self._connection.execute("PRAGMA foreign_keys = OFF")
        self._connection.execute("PRAGMA legacy_alter_table = ON")
        try:
            self._connection.execute("BEGIN")
            self._connection.execute("ALTER TABLE users RENAME TO users_legacy_status_check")
            self._connection.execute(USERS_SCHEMA_SQL)
            self._connection.execute(
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
            self._connection.execute("DROP TABLE users_legacy_status_check")
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise
        finally:
            self._connection.execute("PRAGMA legacy_alter_table = OFF")
            self._connection.execute("PRAGMA foreign_keys = ON")

        broken_references = self._connection.execute("PRAGMA foreign_key_check").fetchall()
        if broken_references:
            msg = "users status schema migration left broken foreign keys"
            raise RuntimeError(msg)

    def _ensure_splitwise_users_schema(self) -> None:
        column_rows = self._connection.execute("PRAGMA table_info(splitwise_users)").fetchall()
        column_names = {str(row["name"]) for row in column_rows}
        if column_names == EXPECTED_SPLITWISE_USERS_COLUMNS:
            return

        row = self._connection.execute("SELECT COUNT(*) FROM splitwise_users").fetchone()
        row_count = 0 if row is None else int(row[0])
        if row_count > 0:
            msg = (
                "splitwise_users has legacy rows. Refusing to recreate it automatically "
                "because that would lose Splitwise links."
            )
            raise RuntimeError(msg)

        self._connection.execute("DROP TABLE splitwise_users")
        self._connection.execute(SPLITWISE_USERS_SCHEMA_SQL)
