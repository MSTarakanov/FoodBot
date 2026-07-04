from __future__ import annotations

from office_food_bot.models import (
    ApprovalKind,
    RegistrationKind,
    TelegramProfile,
    UserStatus,
)
from office_food_bot.repositories import UserRepository
from office_food_bot.services.registration import RegistrationService

DEFAULT_ADMIN_IDS = frozenset({7})


def make_profile(
    telegram_user_id: int = 42,
    username: str | None = "misha",
    first_name: str = "Misha",
    last_name: str | None = None,
) -> TelegramProfile:
    return TelegramProfile(
        telegram_user_id=telegram_user_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
    )


def make_service(
    users: UserRepository,
    admin_ids: frozenset[int] = DEFAULT_ADMIN_IDS,
) -> RegistrationService:
    return RegistrationService(users, admin_ids)


def test_register_new_user_returns_created_pending_user(users: UserRepository) -> None:
    service = make_service(users)

    result = service.register(make_profile(), "  Максим   Т.  ", None)

    assert result.kind == RegistrationKind.CREATED
    assert result.user.display_name == "Максим Т."
    assert result.user.status == UserStatus.PENDING


def test_register_blank_name_falls_back_to_telegram_first_name(
    users: UserRepository,
) -> None:
    service = make_service(users)

    result = service.register(make_profile(first_name="Mikhail"), "   ", None)

    assert result.kind == RegistrationKind.CREATED
    assert result.user.display_name == "Mikhail"


def test_register_truncates_long_display_name(users: UserRepository) -> None:
    service = make_service(users)

    result = service.register(make_profile(), "М" * 80, None)

    assert result.kind == RegistrationKind.CREATED
    assert result.user.display_name == "М" * 64


def test_register_existing_pending_user_updates_request_and_refreshes_telegram_profile(
    users: UserRepository,
) -> None:
    service = make_service(users)
    service.register(make_profile(username="old", first_name="Old"), "Максим", None)

    result = service.register(
        make_profile(username="new", first_name="New", last_name="Name"),
        "Другое",
        None,
    )

    assert result.kind == RegistrationKind.UPDATED_PENDING
    assert result.user.display_name == "Другое"

    user = users.get_by_telegram_id(42)
    assert user is not None
    assert user.display_name == "Другое"
    assert user.username == "new"
    assert user.first_name == "New"
    assert user.last_name == "Name"


def test_register_existing_active_user_returns_already_active(
    users: UserRepository,
) -> None:
    service = make_service(users)
    service.register(make_profile(), "Максим", None)
    service.approve(7, 42)

    result = service.register(make_profile(), "Другое", None)

    assert result.kind == RegistrationKind.ALREADY_ACTIVE
    assert result.user.display_name == "Максим"


def test_re_register_existing_active_user_updates_display_name_and_profile(
    users: UserRepository,
) -> None:
    service = make_service(users)
    service.register(make_profile(username="old", first_name="Old"), "Максим", None)
    service.approve(7, 42)

    user = service.re_register(
        make_profile(username="new", first_name="New", last_name="Name"),
        "  Макс  ",
        None,
    )

    assert user.display_name == "Макс"
    assert user.status == UserStatus.PENDING
    assert user.username == "new"
    assert user.first_name == "New"
    assert user.last_name == "Name"


def test_approve_forbids_non_admin(users: UserRepository) -> None:
    service = make_service(users)
    service.register(make_profile(), "Максим", None)

    result = service.approve(99, 42)

    assert result.kind == ApprovalKind.FORBIDDEN
    assert result.user is None
    user = users.get_by_telegram_id(42)
    assert user is not None
    assert user.status == UserStatus.PENDING


def test_approve_returns_not_found_for_unknown_target(users: UserRepository) -> None:
    service = make_service(users)

    result = service.approve(7, 404)

    assert result.kind == ApprovalKind.NOT_FOUND
    assert result.user is None


def test_approve_activates_pending_user(users: UserRepository) -> None:
    service = make_service(users)
    service.register(make_profile(), "Максим", None)

    result = service.approve(7, 42)

    assert result.kind == ApprovalKind.APPROVED
    assert result.user is not None
    assert result.user.status == UserStatus.ACTIVE


def test_list_pending_requests_is_admin_only(users: UserRepository) -> None:
    service = make_service(users)
    service.register(make_profile(), "Максим", None)

    assert service.list_pending_requests(99) == ()
    assert [
        registration.user.telegram_user_id
        for registration in service.list_pending_requests(7)
    ] == [42]
