from __future__ import annotations

import pytest

from office_food_bot.commanding.errors.models import CommonError, CommonErrorCode
from office_food_bot.models import TelegramProfile
from office_food_bot.repositories import UserRepository
from office_food_bot.services.user_access import ActiveUserResolver


def make_profile() -> TelegramProfile:
    return TelegramProfile(42, "misha", "Misha", None)


def test_active_user_resolver_requires_registration(users: UserRepository) -> None:
    with pytest.raises(CommonError) as error:
        ActiveUserResolver(users).require(42)

    assert error.value.code == CommonErrorCode.REGISTRATION_REQUIRED


def test_active_user_resolver_requires_approved_registration(
    users: UserRepository,
) -> None:
    users.create_pending_user(make_profile(), "Максим")

    with pytest.raises(CommonError) as error:
        ActiveUserResolver(users).require(42)

    assert error.value.code == CommonErrorCode.REGISTRATION_PENDING


def test_active_user_resolver_returns_active_user(users: UserRepository) -> None:
    users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)

    user = ActiveUserResolver(users).require(42)

    assert user.telegram_user_id == 42
    assert user.display_name == "Максим"


def test_active_user_resolver_rejects_inactive_user(users: UserRepository) -> None:
    users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)
    users.abandon_by_telegram_id(42)

    with pytest.raises(CommonError) as error:
        ActiveUserResolver(users).require(42)

    assert error.value.code == CommonErrorCode.REGISTRATION_INACTIVE
