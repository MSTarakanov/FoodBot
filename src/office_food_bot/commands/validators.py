from __future__ import annotations

from office_food_bot.commands.base import CommandContext
from office_food_bot.services.user_access import ActiveUserResolver
from office_food_bot.user_errors import CommonError, CommonErrorCode


class TelegramIdentityValidator:
    def validate(self, context: CommandContext) -> None:
        if context.profile is None:
            raise CommonError(CommonErrorCode.MISSING_TELEGRAM_IDENTITY)


class ActiveUserValidator:
    def __init__(self, users: ActiveUserResolver) -> None:
        self._users = users

    def validate(self, context: CommandContext) -> None:
        profile = context.profile
        if profile is None:
            raise CommonError(CommonErrorCode.MISSING_TELEGRAM_IDENTITY)
        self._users.require(profile.telegram_user_id)
