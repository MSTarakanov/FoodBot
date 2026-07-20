from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from office_food_bot.database import Database
from office_food_bot.infrastructure.persistence.users import UserRepository


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "test.sqlite3")
    database.init_schema()
    try:
        yield database
    finally:
        database.close()


@pytest.fixture
def users(database: Database) -> UserRepository:
    return UserRepository(database)
