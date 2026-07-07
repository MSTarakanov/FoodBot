from __future__ import annotations

import re
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    path: Path

    def migrate(self, connection: sqlite3.Connection) -> None:
        with connection:
            connection.executescript(self.path.read_text())


MIGRATION_FILENAME_PATTERN = re.compile(
    r"^(?P<version>\d{4})_(?P<name>[a-z0-9_]+)\.sql$"
)
MIGRATIONS_PATH = Path(__file__).parent

CURRENT_SCHEMA_VERSION_SQL = "PRAGMA user_version"


def load_migrations() -> tuple[Migration, ...]:
    migrations = tuple(
        _migration_from_path(path)
        for path in sorted(MIGRATIONS_PATH.iterdir())
        if _is_migration_file(path)
    )
    _validate_migrations(migrations)
    return migrations


class MigrationRunner:
    def __init__(
        self,
        connection: sqlite3.Connection,
        migrations: Sequence[Migration],
    ) -> None:
        self._connection = connection
        self._migrations = tuple(migrations)
        _validate_migrations(self._migrations)

    def migrate(self) -> int:
        current_version = self.current_version()
        self._ensure_database_is_not_newer(current_version)
        for migration in self._migrations:
            if migration.version <= current_version:
                continue
            migration.migrate(self._connection)
            self._ensure_foreign_keys_ok(migration)
            self._set_current_version(migration.version)
        return self.current_version()

    def current_version(self) -> int:
        row = self._connection.execute(CURRENT_SCHEMA_VERSION_SQL).fetchone()
        if row is None:
            return 0
        return int(row[0])

    def _set_current_version(self, version: int) -> None:
        with self._connection:
            self._connection.execute(f"PRAGMA user_version = {version}")

    def _ensure_foreign_keys_ok(self, migration: Migration) -> None:
        broken_references = self._connection.execute("PRAGMA foreign_key_check").fetchall()
        if not broken_references:
            return

        msg = f"Migration {migration.version}_{migration.name} left broken foreign keys"
        raise RuntimeError(msg)

    def _ensure_database_is_not_newer(self, current_version: int) -> None:
        latest_known_version = self._latest_known_version()
        if current_version <= latest_known_version:
            return

        msg = f"Database schema version {current_version} is newer than this code"
        raise RuntimeError(msg)

    def _latest_known_version(self) -> int:
        if not self._migrations:
            return 0
        return self._migrations[-1].version


def _validate_migrations(migrations: tuple[Migration, ...]) -> None:
    for expected_version, migration in enumerate(migrations, start=1):
        if migration.version != expected_version:
            msg = "Database migrations must start at 1 and be contiguous"
            raise RuntimeError(msg)


def _is_migration_file(path: Path) -> bool:
    return path.is_file() and MIGRATION_FILENAME_PATTERN.fullmatch(path.name) is not None


def _migration_from_path(path: Path) -> Migration:
    match = MIGRATION_FILENAME_PATTERN.fullmatch(path.name)
    if match is None:
        msg = f"Invalid migration filename: {path.name}"
        raise RuntimeError(msg)

    version = int(match.group("version"))
    name = match.group("name")
    return Migration(version, name, path)
