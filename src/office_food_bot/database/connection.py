from __future__ import annotations

import sqlite3
from pathlib import Path

from office_food_bot.database.database_schema import SCHEMA_SQL


class Database:
    def __init__(self, path: str | Path) -> None:
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

    def close(self) -> None:
        self._connection.close()
