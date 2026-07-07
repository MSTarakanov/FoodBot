from __future__ import annotations

import sqlite3
from pathlib import Path

from office_food_bot.database.migrations import MIGRATIONS, MigrationRunner


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
        MigrationRunner(self._connection, MIGRATIONS).migrate()

    def schema_version(self) -> int:
        return MigrationRunner(self._connection, MIGRATIONS).current_version()

    def close(self) -> None:
        self._connection.close()
