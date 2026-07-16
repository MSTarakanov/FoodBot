from __future__ import annotations

from typing import assert_never

from office_food_bot.application.users.errors import ActiveUserErrorCode
from office_food_bot.commanding.errors.models import CommonErrorCode


def common_error_for_active_user(code: ActiveUserErrorCode) -> CommonErrorCode:
    match code:
        case ActiveUserErrorCode.NOT_REGISTERED:
            return CommonErrorCode.REGISTRATION_REQUIRED
        case ActiveUserErrorCode.PENDING_APPROVAL:
            return CommonErrorCode.REGISTRATION_PENDING
        case ActiveUserErrorCode.INACTIVE:
            return CommonErrorCode.REGISTRATION_INACTIVE
    assert_never(code)
