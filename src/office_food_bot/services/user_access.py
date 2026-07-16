from __future__ import annotations

from office_food_bot.commanding.errors.models import CommonErrorCode
from office_food_bot.models import RegisteredUser, UserStatus
from office_food_bot.repositories import UserRepository
from office_food_bot.result import Result, failure, success


class ActiveUserResolver:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def resolve(
        self,
        telegram_user_id: int,
    ) -> Result[RegisteredUser, CommonErrorCode]:
        user = self._users.get_by_telegram_id(telegram_user_id)
        if user is None:
            return failure(CommonErrorCode.REGISTRATION_REQUIRED)
        if user.status == UserStatus.PENDING:
            return failure(CommonErrorCode.REGISTRATION_PENDING)
        if user.status != UserStatus.ACTIVE:
            return failure(CommonErrorCode.REGISTRATION_INACTIVE)
        return success(user)

    def require_validated(self, telegram_user_id: int) -> RegisteredUser:
        return self.resolve(telegram_user_id).fold(
            lambda user: user,
            _raise_active_user_invariant,
        )


def _raise_active_user_invariant(code: CommonErrorCode) -> RegisteredUser:
    raise RuntimeError(f"Active user was not validated: {code.value}")
