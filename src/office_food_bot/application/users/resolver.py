from __future__ import annotations

from typing import Protocol, assert_never

from office_food_bot.application.users.errors import ActiveUserErrorCode
from office_food_bot.models import RegisteredUser, UserStatus
from office_food_bot.result import Result, failure, success


class ActiveUserRepository(Protocol):
    def get_by_telegram_id(self, telegram_user_id: int) -> RegisteredUser | None: ...


class ActiveUserResolver:
    def __init__(self, users: ActiveUserRepository) -> None:
        self._users = users

    def resolve(
        self,
        telegram_user_id: int,
    ) -> Result[RegisteredUser, ActiveUserErrorCode]:
        user = self._users.get_by_telegram_id(telegram_user_id)
        if user is None:
            return failure(ActiveUserErrorCode.NOT_REGISTERED)
        match user.status:
            case UserStatus.PENDING:
                return failure(ActiveUserErrorCode.PENDING_APPROVAL)
            case UserStatus.REJECTED | UserStatus.DISABLED | UserStatus.ABANDONED:
                return failure(ActiveUserErrorCode.INACTIVE)
            case UserStatus.ACTIVE:
                return success(user)
        assert_never(user.status)

    def require_active(self, telegram_user_id: int) -> RegisteredUser:
        return self.resolve(telegram_user_id).fold(
            lambda user: user,
            _raise_active_user_invariant,
        )


def _raise_active_user_invariant(code: ActiveUserErrorCode) -> RegisteredUser:
    raise RuntimeError(f"Active user was not validated: {code.value}")
