from __future__ import annotations

from office_food_bot.repositories import DebugRepository


class DebugService:
    def __init__(self, debug_settings: DebugRepository) -> None:
        self._debug_settings = debug_settings

    def is_enabled(self, telegram_user_id: int) -> bool:
        return self._debug_settings.is_enabled(telegram_user_id)

    def set_enabled(self, telegram_user_id: int, enabled: bool) -> None:
        self._debug_settings.set_enabled(telegram_user_id, enabled)
