from __future__ import annotations

from office_food_bot.database import Database
from office_food_bot.features.debug.queries import (
    GET_TELEGRAM_DEBUG_ENABLED_SQL,
    UPSERT_TELEGRAM_DEBUG_SQL,
)


class DebugRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def is_enabled(self, telegram_user_id: int) -> bool:
        row = self._database.connection.execute(
            GET_TELEGRAM_DEBUG_ENABLED_SQL,
            (telegram_user_id,),
        ).fetchone()
        if row is None:
            return False
        return bool(row["enabled"])

    def set_enabled(self, telegram_user_id: int, enabled: bool) -> None:
        with self._database.connection:
            self._database.connection.execute(
                UPSERT_TELEGRAM_DEBUG_SQL,
                (telegram_user_id, int(enabled)),
            )
