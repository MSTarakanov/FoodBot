from __future__ import annotations

from office_food_bot.commanding.contracts import CommandContext
from office_food_bot.commanding.errors.models import CommonError, CommonErrorCode
from office_food_bot.models import TelegramProfile
from office_food_bot.services.user_access import ActiveUserResolver


class TelegramIdentityValidator:
    def validate(self, context: CommandContext) -> None:
        require_telegram_profile(context)


class ActiveUserValidator:
    def __init__(self, users: ActiveUserResolver) -> None:
        self._users = users

    def validate[RequestT](self, context: CommandContext, request: RequestT) -> None:
        del request
        profile = require_telegram_profile(context)
        self._users.require(profile.telegram_user_id)


def require_telegram_profile(context: CommandContext) -> TelegramProfile:
    if context.profile is None:
        raise CommonError(CommonErrorCode.MISSING_TELEGRAM_IDENTITY)
    return context.profile
