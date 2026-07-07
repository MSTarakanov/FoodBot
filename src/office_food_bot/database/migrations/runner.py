from __future__ import annotations

import re
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Protocol


class MigrationStep(Protocol):
    def __call__(self, connection: sqlite3.Connection) -> None: ...


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    migrate: MigrationStep


@dataclass(frozen=True)
class SqlMigrationStep:
    path: Path

    def __call__(self, connection: sqlite3.Connection) -> None:
        with connection:
            connection.executescript(self.path.read_text())


@dataclass(frozen=True)
class PythonMigrationStep:
    module_name: str

    def __call__(self, connection: sqlite3.Connection) -> None:
        module = import_module(self.module_name)
        migrate = getattr(module, "migrate", None)
        if not callable(migrate):
            msg = f"Python migration {self.module_name} must define migrate(connection)"
            raise RuntimeError(msg)
        migrate(connection)


MIGRATION_FILENAME_PATTERN = re.compile(
    r"^(?P<version>\d{4})_(?P<name>[a-z0-9_]+)\.(?P<kind>sql|py)$"
)
MIGRATIONS_PACKAGE = "office_food_bot.database.migrations"
MIGRATIONS_PATH = Path(__file__).parent

SCHEMA_MIGRATIONS_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

LIST_APPLIED_MIGRATIONS_SQL = """
SELECT version
FROM schema_migrations
ORDER BY version
"""

INSERT_SCHEMA_MIGRATION_SQL = """
INSERT INTO schema_migrations (version, name)
VALUES (?, ?)
"""

CURRENT_SCHEMA_VERSION_SQL = """
SELECT COALESCE(MAX(version), 0)
FROM schema_migrations
"""

SCHEMA_MIGRATIONS_EXISTS_SQL = """
SELECT 1
FROM sqlite_master
WHERE type = 'table' AND name = 'schema_migrations'
"""

TABLE_EXISTS_SQL = """
SELECT 1
FROM sqlite_master
WHERE type = 'table' AND name = ?
"""

USERS_TABLE_SQL = """
SELECT sql
FROM sqlite_master
WHERE type = 'table' AND name = 'users'
"""


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
        schema_migrations_existed = self._schema_migrations_table_exists()
        self._ensure_schema_migrations_table()
        if not schema_migrations_existed:
            self._record_reflected_pre_migration_versions()
        applied_versions = self._applied_versions()
        self._ensure_no_unknown_migrations(applied_versions)
        for migration in self._migrations:
            if migration.version in applied_versions:
                continue
            migration.migrate(self._connection)
            self._ensure_foreign_keys_ok(migration)
            self._record_migration(migration)
        return self.current_version()

    def current_version(self) -> int:
        self._ensure_schema_migrations_table()
        row = self._connection.execute(CURRENT_SCHEMA_VERSION_SQL).fetchone()
        if row is None:
            return 0
        return int(row[0])

    def _ensure_schema_migrations_table(self) -> None:
        with self._connection:
            self._connection.execute(SCHEMA_MIGRATIONS_SQL)

    def _schema_migrations_table_exists(self) -> bool:
        return self._connection.execute(SCHEMA_MIGRATIONS_EXISTS_SQL).fetchone() is not None

    def _applied_versions(self) -> frozenset[int]:
        rows = self._connection.execute(LIST_APPLIED_MIGRATIONS_SQL).fetchall()
        return frozenset(int(row["version"]) for row in rows)

    def _record_migration(self, migration: Migration) -> None:
        with self._connection:
            self._connection.execute(
                INSERT_SCHEMA_MIGRATION_SQL,
                (migration.version, migration.name),
            )

    def _record_reflected_pre_migration_versions(self) -> None:
        # Existing databases created before schema_migrations need a one-time baseline.
        reflected_migrations = []
        for migration in self._migrations:
            if not self._migration_is_reflected_in_current_schema(migration):
                break
            reflected_migrations.append(migration)

        if not reflected_migrations:
            return

        with self._connection:
            for migration in reflected_migrations:
                self._connection.execute(
                    INSERT_SCHEMA_MIGRATION_SQL,
                    (migration.version, migration.name),
                )

    def _migration_is_reflected_in_current_schema(self, migration: Migration) -> bool:
        if migration.version == 1:
            return self._has_initial_schema()
        if migration.version == 2:
            return self._has_splitwise_email_schema()
        if migration.version == 3:
            return self._users_status_allows_abandoned()
        if migration.version == 4:
            return self._table_exists("telegram_debug_settings")
        if migration.version == 5:
            return self._table_exists("lunch_auto_chats")
        if migration.version == 6:
            return self._splitwise_email_is_nullable()
        if migration.version == 7:
            return self._table_exists("user_vacations")
        if migration.version == 8:
            return self._table_exists("telegram_seen_accounts")
        return False

    def _has_initial_schema(self) -> bool:
        return (
            self._table_exists("users")
            and self._table_exists("telegram_accounts")
            and self._table_exists("splitwise_users")
        )

    def _has_splitwise_email_schema(self) -> bool:
        splitwise_columns = self._column_names("splitwise_users")
        return "email" in splitwise_columns and "display_name" not in splitwise_columns

    def _users_status_allows_abandoned(self) -> bool:
        users_sql = self._users_table_sql()
        return users_sql is not None and "'abandoned'" in users_sql

    def _splitwise_email_is_nullable(self) -> bool:
        rows = self._connection.execute("PRAGMA table_info(splitwise_users)").fetchall()
        for row in rows:
            if str(row["name"]) == "email":
                return int(row["notnull"]) == 0
        return False

    def _table_exists(self, table_name: str) -> bool:
        return self._connection.execute(TABLE_EXISTS_SQL, (table_name,)).fetchone() is not None

    def _users_table_sql(self) -> str | None:
        row = self._connection.execute(USERS_TABLE_SQL).fetchone()
        if row is None:
            return None
        return str(row["sql"])

    def _column_names(self, table_name: str) -> frozenset[str]:
        rows = self._connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        return frozenset(str(row["name"]) for row in rows)

    def _ensure_foreign_keys_ok(self, migration: Migration) -> None:
        broken_references = self._connection.execute("PRAGMA foreign_key_check").fetchall()
        if not broken_references:
            return

        msg = f"Migration {migration.version}_{migration.name} left broken foreign keys"
        raise RuntimeError(msg)

    def _ensure_no_unknown_migrations(self, applied_versions: frozenset[int]) -> None:
        known_versions = frozenset(migration.version for migration in self._migrations)
        unknown_versions = sorted(applied_versions - known_versions)
        if not unknown_versions:
            return

        versions = ", ".join(str(version) for version in unknown_versions)
        msg = f"Database schema has migrations newer than this code: {versions}"
        raise RuntimeError(msg)


def _validate_migrations(migrations: tuple[Migration, ...]) -> None:
    previous_version = 0
    for migration in migrations:
        if migration.version <= previous_version:
            msg = "Database migrations must be ordered by unique increasing versions"
            raise RuntimeError(msg)
        previous_version = migration.version


def _is_migration_file(path: Path) -> bool:
    return path.is_file() and MIGRATION_FILENAME_PATTERN.fullmatch(path.name) is not None


def _migration_from_path(path: Path) -> Migration:
    match = MIGRATION_FILENAME_PATTERN.fullmatch(path.name)
    if match is None:
        msg = f"Invalid migration filename: {path.name}"
        raise RuntimeError(msg)

    version = int(match.group("version"))
    name = match.group("name")
    kind = match.group("kind")
    if kind == "sql":
        return Migration(version, name, SqlMigrationStep(path))
    return Migration(version, name, PythonMigrationStep(f"{MIGRATIONS_PACKAGE}.{path.stem}"))
