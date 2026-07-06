from __future__ import annotations

from office_food_bot.database import Database
from office_food_bot.repositories import DebugRepository, UserRepository
from office_food_bot.services.command_access import (
    CommandAccessService,
    CommandAccessStatus,
)
from office_food_bot.services.debug import DebugService
from office_food_bot.services.registration import RegistrationService


def make_access_service(database: Database) -> CommandAccessService:
    registration = RegistrationService(UserRepository(database), frozenset({7}))
    debug = DebugService(DebugRepository(database))
    return CommandAccessService(registration, debug)


def test_private_only_command_is_forbidden_in_group(database: Database) -> None:
    result = make_access_service(database).can_run("register", "group", 42)

    assert not result.allowed
    assert result.status == CommandAccessStatus.PRIVATE_ONLY


def test_group_only_command_is_forbidden_in_private(database: Database) -> None:
    result = make_access_service(database).can_run("lunch", "private", 42)

    assert not result.allowed
    assert result.status == CommandAccessStatus.GROUP_ONLY


def test_any_command_is_allowed_in_private_and_group(database: Database) -> None:
    access = make_access_service(database)

    assert access.can_run("balance", "private", 42).allowed
    assert access.can_run("balance", "group", 42).allowed


def test_group_only_command_is_allowed_for_private_admin_debug(
    database: Database,
) -> None:
    debug = DebugRepository(database)
    access = make_access_service(database)

    assert not access.can_run("lunch", "private", 7).allowed

    debug.set_enabled(7, True)

    assert access.can_run("lunch", "private", 7).allowed


def test_admin_only_command_is_forbidden_for_non_admin(database: Database) -> None:
    result = make_access_service(database).can_run("approve", "private", 42)

    assert not result.allowed
    assert result.status == CommandAccessStatus.ADMIN_ONLY


def test_admin_only_command_is_allowed_for_admin(database: Database) -> None:
    assert make_access_service(database).can_run("approve", "private", 7).allowed


def test_debug_command_is_forbidden_in_group(database: Database) -> None:
    result = make_access_service(database).can_run("debug", "group", 7)

    assert not result.allowed
    assert result.status == CommandAccessStatus.PRIVATE_ONLY
