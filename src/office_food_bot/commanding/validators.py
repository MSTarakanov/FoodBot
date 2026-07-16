from __future__ import annotations

from office_food_bot.commanding.contracts import CommandContext
from office_food_bot.commanding.errors.models import CommonErrorCode
from office_food_bot.models import TelegramProfile
from office_food_bot.result import Result, failure, success
from office_food_bot.services.user_access import ActiveUserResolver


class TelegramIdentityValidator:
    def validate(
        self,
        context: CommandContext,
    ) -> Result[None, CommonErrorCode]:
        if context.profile is None:
            return failure(CommonErrorCode.MISSING_TELEGRAM_IDENTITY)
        return success(None)


class ActiveUserValidator:
    def __init__(self, users: ActiveUserResolver) -> None:
        self._users = users

    def validate[RequestT](
        self,
        context: CommandContext,
        request: RequestT,
    ) -> Result[None, CommonErrorCode]:
        del request
        profile = require_telegram_profile(context)
        return self._users.resolve(profile.telegram_user_id).map(lambda _: None)


def require_telegram_profile(context: CommandContext) -> TelegramProfile:
    if context.profile is None:
        raise RuntimeError("Validated command context has no Telegram identity")
    return context.profile
