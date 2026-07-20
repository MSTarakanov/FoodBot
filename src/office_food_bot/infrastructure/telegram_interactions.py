from __future__ import annotations

from typing import Protocol

from office_food_bot.application.users.models import TelegramProfile


class TelegramAccountRecorder(Protocol):
    def remember(self, profile: TelegramProfile) -> None: ...


class TelegramInteractionService:
    def __init__(
        self,
        telegram_accounts: TelegramAccountRecorder,
    ) -> None:
        self._telegram_accounts = telegram_accounts

    def remember(self, profile: TelegramProfile) -> None:
        self._telegram_accounts.remember(profile)
