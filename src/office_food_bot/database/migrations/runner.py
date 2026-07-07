from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class MigrationStep(Protocol):
    def __call__(self, connection: sqlite3.Connection) -> None: ...


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    migrate: MigrationStep


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
        self._ensure_schema_migrations_table()
        applied_versions = self._applied_versions()
        self._ensure_no_unknown_migrations(applied_versions)
        for migration in self._migrations:
            if migration.version in applied_versions:
                continue
            migration.migrate(self._connection)
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

    def _applied_versions(self) -> frozenset[int]:
        rows = self._connection.execute(LIST_APPLIED_MIGRATIONS_SQL).fetchall()
        return frozenset(int(row["version"]) for row in rows)

    def _record_migration(self, migration: Migration) -> None:
        with self._connection:
            self._connection.execute(
                INSERT_SCHEMA_MIGRATION_SQL,
                (migration.version, migration.name),
            )

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
