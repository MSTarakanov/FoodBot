from __future__ import annotations

import pytest

from office_food_bot.application.users.errors import ActiveUserErrorCode
from office_food_bot.application.users.resolver import ActiveUserResolver
from office_food_bot.models import RegisteredUser, TelegramProfile
from office_food_bot.repositories import UserRepository
from office_food_bot.result import Failure


def make_profile() -> TelegramProfile:
    return TelegramProfile(42, "misha", "Misha", None)


def test_active_user_resolver_requires_registration(users: UserRepository) -> None:
    assert ActiveUserResolver(users).resolve(42) == Failure[
        RegisteredUser,
        ActiveUserErrorCode,
    ](ActiveUserErrorCode.NOT_REGISTERED)


def test_active_user_resolver_requires_approved_registration(
    users: UserRepository,
) -> None:
    users.create_pending_user(make_profile(), "Максим")

    assert ActiveUserResolver(users).resolve(42) == Failure[
        RegisteredUser,
        ActiveUserErrorCode,
    ](ActiveUserErrorCode.PENDING_APPROVAL)


def test_active_user_resolver_returns_active_user(users: UserRepository) -> None:
    users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)

    user = ActiveUserResolver(users).resolve(42).fold(
        lambda resolved: resolved,
        lambda code: pytest.fail(f"Unexpected active user error: {code}"),
    )

    assert user.telegram_user_id == 42
    assert user.display_name == "Максим"


def test_active_user_resolver_rejects_inactive_user(users: UserRepository) -> None:
    users.create_pending_user(make_profile(), "Максим")
    users.approve_by_telegram_id(42)
    users.abandon_by_telegram_id(42)

    assert ActiveUserResolver(users).resolve(42) == Failure[
        RegisteredUser,
        ActiveUserErrorCode,
    ](ActiveUserErrorCode.INACTIVE)
