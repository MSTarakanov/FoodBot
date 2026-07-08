from __future__ import annotations

from office_food_bot.models import TelegramProfile
from office_food_bot.repositories import TelegramSeenRepository, UserRepository


class TelegramInteractionService:
    def __init__(
        self,
        seen_accounts: TelegramSeenRepository,
        users: UserRepository,
    ) -> None:
        self._seen_accounts = seen_accounts
        self._users = users

    def remember(self, profile: TelegramProfile) -> None:
        self._seen_accounts.remember(profile)
        if self._users.get_by_telegram_id(profile.telegram_user_id) is not None:
            self._users.refresh_telegram_profile(profile)
