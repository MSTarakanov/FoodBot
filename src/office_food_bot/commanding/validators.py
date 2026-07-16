from __future__ import annotations

from typing import Protocol

from office_food_bot.application.users.errors import ActiveUserErrorCode
from office_food_bot.application.users.models import RegisteredUser, TelegramProfile
from office_food_bot.commanding.contracts import CommandContext
from office_food_bot.commanding.errors.mapping import common_error_for_active_user
from office_food_bot.commanding.errors.models import CommonErrorCode
from office_food_bot.result import Result, failure, success


class TelegramIdentityValidator:
    def validate(
        self,
        context: CommandContext,
    ) -> Result[None, CommonErrorCode]:
        if context.profile is None:
            return failure(CommonErrorCode.MISSING_TELEGRAM_IDENTITY)
        return success(None)


class ActiveUserAccess(Protocol):
    def resolve(
        self,
        telegram_user_id: int,
    ) -> Result[RegisteredUser, ActiveUserErrorCode]: ...


class ActiveUserValidator:
    def __init__(self, users: ActiveUserAccess) -> None:
        self._users = users

    def validate(
        self,
        context: CommandContext,
    ) -> Result[None, CommonErrorCode]:
        profile = require_telegram_profile(context)
        return self._users.resolve(profile.telegram_user_id).fold(
            lambda _: success(None),
            lambda code: failure(common_error_for_active_user(code)),
        )


def require_telegram_profile(context: CommandContext) -> TelegramProfile:
    if context.profile is None:
        raise RuntimeError("Validated command context has no Telegram identity")
    return context.profile
