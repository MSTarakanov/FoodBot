from __future__ import annotations

from office_food_bot.models import TelegramProfile
from office_food_bot.repositories import TelegramSeenRepository


class TelegramInteractionService:
    def __init__(self, seen_accounts: TelegramSeenRepository) -> None:
        self._seen_accounts = seen_accounts

    def remember(self, profile: TelegramProfile) -> None:
        self._seen_accounts.remember(profile)
