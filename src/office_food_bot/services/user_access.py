from __future__ import annotations

from office_food_bot.commanding.errors.models import CommonError, CommonErrorCode
from office_food_bot.models import RegisteredUser, UserStatus
from office_food_bot.repositories import UserRepository


class ActiveUserResolver:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def require(self, telegram_user_id: int) -> RegisteredUser:
        user = self._users.get_by_telegram_id(telegram_user_id)
        if user is None:
            raise CommonError(CommonErrorCode.REGISTRATION_REQUIRED)
        if user.status == UserStatus.PENDING:
            raise CommonError(CommonErrorCode.REGISTRATION_PENDING)
        if user.status != UserStatus.ACTIVE:
            raise CommonError(CommonErrorCode.REGISTRATION_INACTIVE)
        return user
