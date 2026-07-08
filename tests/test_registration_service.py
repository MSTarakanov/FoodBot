from __future__ import annotations

from office_food_bot.database import Database
from office_food_bot.models import (
    ApprovalKind,
    RegistrationKind,
    SplitwiseMember,
    TelegramProfile,
    UserStatus,
)
from office_food_bot.repositories import TelegramAccountRepository, UserRepository
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
    database: Database,
    admin_ids: frozenset[int] = DEFAULT_ADMIN_IDS,
) -> RegistrationService:
    return RegistrationService(
        UserRepository(database),
        TelegramAccountRepository(database),
        admin_ids,
    )


def make_splitwise_member(
    splitwise_user_id: int = 1001,
    email: str = "max@example.com",
) -> SplitwiseMember:
    return SplitwiseMember(
        splitwise_user_id=splitwise_user_id,
        first_name="Max",
        last_name=None,
        email=email,
    )


def test_register_new_user_returns_created_pending_user(
    database: Database,
    users: UserRepository,
) -> None:
    service = make_service(database)

    result = service.register(make_profile(), "  Максим   Т.  ", None)

    assert result.kind == RegistrationKind.CREATED
    assert result.user.display_name == "Максим Т."
    assert result.user.status == UserStatus.PENDING


def test_register_blank_name_falls_back_to_telegram_first_name(
    database: Database,
    users: UserRepository,
) -> None:
    service = make_service(database)

    result = service.register(make_profile(first_name="Mikhail"), "   ", None)

    assert result.kind == RegistrationKind.CREATED
    assert result.user.display_name == "Mikhail"


def test_register_blank_name_falls_back_to_telegram_full_name(
    database: Database,
    users: UserRepository,
) -> None:
    service = make_service(database)

    result = service.register(
        make_profile(first_name="Mikhail", last_name="Tarakanov"),
        "   ",
        None,
    )

    assert result.kind == RegistrationKind.CREATED
    assert result.user.display_name == "Mikhail Tarakanov"


def test_register_truncates_long_display_name(
    database: Database,
    users: UserRepository,
) -> None:
    service = make_service(database)

    result = service.register(make_profile(), "М" * 80, None)

    assert result.kind == RegistrationKind.CREATED
    assert result.user.display_name == "М" * 64


def test_register_existing_pending_user_updates_request_and_refreshes_telegram_profile(
    database: Database,
    users: UserRepository,
) -> None:
    service = make_service(database)
    service.register(make_profile(username="old", first_name="Old"), "Максим", None)

    result = service.register(
        make_profile(username="new", first_name="New", last_name="Name"),
        "Другое",
        None,
    )

    assert result.kind == RegistrationKind.UPDATED_PENDING
    assert result.user.display_name == "Другое"
    assert result.previous_details is not None
    assert result.previous_details.display_name == "Максим"

    user = users.get_by_telegram_id(42)
    assert user is not None
    assert user.display_name == "Другое"
    assert user.username == "new"
    assert user.first_name == "New"
    assert user.last_name == "Name"


def test_register_existing_pending_user_with_same_data_is_noop_but_refreshes_profile(
    database: Database,
    users: UserRepository,
) -> None:
    service = make_service(database)
    splitwise_member = make_splitwise_member()
    service.register(make_profile(username="old", first_name="Old"), "Максим", splitwise_member)

    result = service.register(
        make_profile(username="new", first_name="New", last_name="Name"),
        "  Максим  ",
        splitwise_member,
    )

    assert result.kind == RegistrationKind.ALREADY_PENDING
    assert result.user.display_name == "Максим"
    assert result.user.username == "new"
    assert result.user.first_name == "New"
    assert result.user.last_name == "Name"

    pending_registrations = users.list_pending_registrations()
    assert len(pending_registrations) == 1
    assert pending_registrations[0].splitwise is not None
    assert pending_registrations[0].splitwise.email == "max@example.com"


def test_register_existing_active_user_returns_already_active(
    database: Database,
    users: UserRepository,
) -> None:
    service = make_service(database)
    service.register(make_profile(), "Максим", None)
    service.approve(7, 42)

    result = service.register(make_profile(), "Другое", None)

    assert result.kind == RegistrationKind.ALREADY_ACTIVE
    assert result.user.display_name == "Максим"
    assert result.previous_details is not None
    assert result.previous_details.display_name == "Максим"


def test_register_existing_abandoned_user_creates_new_pending_request(
    database: Database,
    users: UserRepository,
) -> None:
    service = make_service(database)
    service.register(make_profile(), "Максим", None)
    assert service.quit_registration(42)

    result = service.register(make_profile(username="new"), "Другое", None)

    assert result.kind == RegistrationKind.CREATED
    assert result.user.display_name == "Другое"
    assert result.user.status == UserStatus.PENDING
    assert result.user.username == "new"


def test_re_register_existing_active_user_updates_display_name_and_profile(
    database: Database,
    users: UserRepository,
) -> None:
    service = make_service(database)
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


def test_approve_forbids_non_admin(database: Database, users: UserRepository) -> None:
    service = make_service(database)
    service.register(make_profile(), "Максим", None)

    result = service.approve(99, 42)

    assert result.kind == ApprovalKind.FORBIDDEN
    assert result.user is None
    user = users.get_by_telegram_id(42)
    assert user is not None
    assert user.status == UserStatus.PENDING


def test_request_registration_block_reason_depends_on_status(
    database: Database,
    users: UserRepository,
) -> None:
    service = make_service(database)

    assert service.request_registration_block_reason(42) is None

    service.register(make_profile(), "Максим", None)
    assert service.request_registration_block_reason(42) == (
        "Заявка уже ждет аппрува. Если хотите отменить регистрацию, отправьте /quit."
    )

    service.approve(7, 42)
    assert service.request_registration_block_reason(42) == (
        "Вы уже зарегистрированы. Если хотите отрегистрироваться, отправьте /quit."
    )

    assert service.quit_registration(42)
    assert service.request_registration_block_reason(42) is None


def test_quit_registration_returns_false_for_unknown_or_abandoned_user(
    database: Database,
    users: UserRepository,
) -> None:
    service = make_service(database)

    assert not service.quit_registration(42)

    service.register(make_profile(), "Максим", None)
    assert service.quit_registration(42)
    assert not service.quit_registration(42)


def test_approve_returns_not_found_for_unknown_target(database: Database) -> None:
    service = make_service(database)

    result = service.approve(7, 404)

    assert result.kind == ApprovalKind.NOT_FOUND
    assert result.user is None


def test_approve_activates_pending_user(
    database: Database,
    users: UserRepository,
) -> None:
    service = make_service(database)
    service.register(make_profile(), "Максим", None)

    result = service.approve(7, 42)

    assert result.kind == ApprovalKind.APPROVED
    assert result.user is not None
    assert result.user.status == UserStatus.ACTIVE


def test_list_pending_requests_is_admin_only(
    database: Database,
    users: UserRepository,
) -> None:
    service = make_service(database)
    service.register(make_profile(), "Максим", None)

    assert service.list_pending_requests(99) == ()
    assert [
        registration.user.telegram_user_id
        for registration in service.list_pending_requests(7)
    ] == [42]


def test_registration_profile_for_telegram_id_uses_known_telegram_account(
    database: Database,
) -> None:
    TelegramAccountRepository(database).remember(
        make_profile(
            telegram_user_id=42,
            username="misha",
            first_name="Misha",
            last_name="Petrov",
        )
    )
    service = make_service(database)

    profile = service.registration_profile_for_telegram_id(42)

    assert profile == TelegramProfile(
        telegram_user_id=42,
        username="misha",
        first_name="Misha",
        last_name="Petrov",
    )


def test_list_unregistered_telegram_accounts_is_admin_only(database: Database) -> None:
    TelegramAccountRepository(database).remember(make_profile())
    service = make_service(database)

    assert service.list_unregistered_telegram_accounts(99) == ()
    assert [
        account.telegram_user_id
        for account in service.list_unregistered_telegram_accounts(7)
    ] == [42]
