from __future__ import annotations

from office_food_bot.models import TelegramProfile
from office_food_bot.repositories import TelegramAccountRepository


class TelegramInteractionService:
    def __init__(
        self,
        telegram_accounts: TelegramAccountRepository,
    ) -> None:
        self._telegram_accounts = telegram_accounts

    def remember(self, profile: TelegramProfile) -> None:
        self._telegram_accounts.remember(profile)
