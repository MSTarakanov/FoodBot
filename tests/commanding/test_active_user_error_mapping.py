from __future__ import annotations

import pytest

from office_food_bot.application.users.errors import ActiveUserErrorCode
from office_food_bot.commanding.errors.mapping import common_error_for_active_user
from office_food_bot.commanding.errors.models import CommonErrorCode


@pytest.mark.parametrize(
    ("application_error", "common_error"),
    (
        (ActiveUserErrorCode.NOT_REGISTERED, CommonErrorCode.REGISTRATION_REQUIRED),
        (ActiveUserErrorCode.PENDING_APPROVAL, CommonErrorCode.REGISTRATION_PENDING),
        (ActiveUserErrorCode.INACTIVE, CommonErrorCode.REGISTRATION_INACTIVE),
    ),
)
def test_active_user_error_maps_to_common_command_error(
    application_error: ActiveUserErrorCode,
    common_error: CommonErrorCode,
) -> None:
    assert common_error_for_active_user(application_error) == common_error
