from __future__ import annotations

from office_food_bot.commands.approve import ApproveCommand
from office_food_bot.commands.balance import BalanceCommand
from office_food_bot.commands.debug import DebugCommand
from office_food_bot.commands.lunch import LunchCommand
from office_food_bot.commands.register import RegisterCommand, RequestRegisterCommand
from office_food_bot.commands.test_message import TestMessageCommand as PreviewTestMessageCommand
from office_food_bot.database import Database
from office_food_bot.repositories import (
    DebugRepository,
    RegistrationRequestRepository,
    TelegramAccountRepository,
    UserRepository,
)
from office_food_bot.services.command_access import (
    CommandAccessDenialReason,
    CommandAccessService,
)
from office_food_bot.services.debug import DebugService
from office_food_bot.services.registration import RegistrationService


def make_access_service(database: Database) -> CommandAccessService:
    registration = RegistrationService(
        UserRepository(database),
        TelegramAccountRepository(database),
        RegistrationRequestRepository(database),
        frozenset({7}),
    )
    debug = DebugService(DebugRepository(database))
    return CommandAccessService(registration, debug)


def test_private_only_command_is_forbidden_in_group(database: Database) -> None:
    result = make_access_service(database).can_run(RegisterCommand.definition, "group", 42)

    assert not result.allowed
    assert result.denial_reason == CommandAccessDenialReason.PRIVATE_ONLY


def test_group_only_command_is_forbidden_in_private(database: Database) -> None:
    result = make_access_service(database).can_run(
        LunchCommand.definition,
        "private",
        42,
        "rose",
    )

    assert not result.allowed
    assert result.denial_reason == CommandAccessDenialReason.GROUP_ONLY


def test_any_command_is_allowed_in_private_and_group(database: Database) -> None:
    access = make_access_service(database)

    assert access.can_run(BalanceCommand.definition, "private", 42).allowed
    assert access.can_run(BalanceCommand.definition, "group", 42).allowed


def test_group_only_command_is_allowed_for_private_admin_debug(
    database: Database,
) -> None:
    debug = DebugRepository(database)
    access = make_access_service(database)

    assert not access.can_run(LunchCommand.definition, "private", 7, "rose").allowed

    debug.set_enabled(7, True)

    assert access.can_run(LunchCommand.definition, "private", 7, "rose").allowed


def test_lunch_status_and_toggles_are_allowed_in_private(database: Database) -> None:
    access = make_access_service(database)

    assert access.can_run(LunchCommand.definition, "private", 42).allowed
    assert access.can_run(LunchCommand.definition, "private", 42, "on").allowed
    assert access.can_run(LunchCommand.definition, "private", 42, "off").allowed


def test_request_register_is_allowed_in_group_but_hidden_from_menu(
    database: Database,
) -> None:
    access = make_access_service(database)

    definitions = (RequestRegisterCommand.definition,)

    assert access.can_run(RequestRegisterCommand.definition, "group", 42).allowed
    assert "request_register" not in {
        command.name for command in access.visible_commands(definitions, "group", 42)
    }


def test_admin_only_command_is_forbidden_for_non_admin(database: Database) -> None:
    result = make_access_service(database).can_run(ApproveCommand.definition, "private", 42)

    assert not result.allowed
    assert result.denial_reason == CommandAccessDenialReason.ADMIN_ONLY


def test_admin_only_command_is_allowed_for_admin(database: Database) -> None:
    assert (
        make_access_service(database)
        .can_run(
            ApproveCommand.definition,
            "private",
            7,
        )
        .allowed
    )


def test_debug_command_is_forbidden_in_group(database: Database) -> None:
    result = make_access_service(database).can_run(DebugCommand.definition, "group", 7)

    assert not result.allowed
    assert result.denial_reason == CommandAccessDenialReason.PRIVATE_ONLY


def test_test_command_is_private_admin_only_and_hidden_from_menu(
    database: Database,
) -> None:
    access = make_access_service(database)

    definitions = (PreviewTestMessageCommand.definition,)

    assert access.can_run(PreviewTestMessageCommand.definition, "private", 7).allowed
    assert not access.can_run(
        PreviewTestMessageCommand.definition,
        "private",
        42,
    ).allowed
    assert not access.can_run(
        PreviewTestMessageCommand.definition,
        "group",
        7,
    ).allowed
    assert "test" not in {
        command.name for command in access.visible_commands(definitions, "private", 7)
    }
    assert "test" in {
        entry.command_name for entry in access.visible_help_entries(definitions, "private", 7)
    }
