from __future__ import annotations

import sqlite3
from pathlib import Path

from office_food_bot.database.database_schema import SCHEMA_SQL, SPLITWISE_USERS_SCHEMA_SQL

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
            self._ensure_splitwise_users_schema()

    def close(self) -> None:
        self._connection.close()

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
