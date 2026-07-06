from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from office_food_bot.commands.definitions import (
    COMMANDS,
    CommandDefinition,
    CommandScope,
    command_definition,
)
from office_food_bot.services.debug import DebugService
from office_food_bot.services.registration import RegistrationService

PRIVATE_CHAT_TYPE = "private"
GROUP_CHAT_TYPES = frozenset({"group", "supergroup"})


class CommandAccessStatus(StrEnum):
    ALLOWED = "allowed"
    PRIVATE_ONLY = "private_only"
    GROUP_ONLY = "group_only"
    ADMIN_ONLY = "admin_only"


@dataclass(frozen=True)
class CommandAccessResult:
    status: CommandAccessStatus

    @property
    def allowed(self) -> bool:
        return self.status == CommandAccessStatus.ALLOWED


class CommandAccessService:
    def __init__(
        self,
        registration: RegistrationService,
        debug: DebugService,
    ) -> None:
        self._registration = registration
        self._debug = debug

    def can_run(
        self,
        command_name: str,
        chat_type: str,
        telegram_user_id: int | None,
    ) -> CommandAccessResult:
        definition = command_definition(command_name)
        if definition is None:
            return _allowed()

        if definition.scope == CommandScope.PRIVATE and chat_type != PRIVATE_CHAT_TYPE:
            return CommandAccessResult(CommandAccessStatus.PRIVATE_ONLY)

        if (
            definition.scope == CommandScope.GROUP
            and not self._can_run_group_command_in_chat(chat_type, telegram_user_id)
        ):
            return CommandAccessResult(CommandAccessStatus.GROUP_ONLY)

        if definition.admin_only and not self.is_admin(telegram_user_id):
            return CommandAccessResult(CommandAccessStatus.ADMIN_ONLY)

        return _allowed()

    def visible_commands(
        self,
        chat_type: str,
        telegram_user_id: int | None,
    ) -> tuple[CommandDefinition, ...]:
        return tuple(
            definition
            for definition in COMMANDS
            if self.can_run(definition.name, chat_type, telegram_user_id).allowed
        )

    def admin_chat_ids_for_menu(self) -> tuple[int, ...]:
        return tuple(sorted(self._registration.admin_ids))

    def is_admin(self, telegram_user_id: int | None) -> bool:
        if telegram_user_id is None:
            return False
        return self._registration.can_approve(telegram_user_id)

    def is_debug_enabled(self, telegram_user_id: int | None) -> bool:
        if telegram_user_id is None:
            return False
        return self._debug.is_enabled(telegram_user_id)

    def _can_run_group_command_in_chat(
        self,
        chat_type: str,
        telegram_user_id: int | None,
    ) -> bool:
        if chat_type in GROUP_CHAT_TYPES:
            return True
        return (
            chat_type == PRIVATE_CHAT_TYPE
            and self.is_admin(telegram_user_id)
            and self.is_debug_enabled(telegram_user_id)
        )


def _allowed() -> CommandAccessResult:
    return CommandAccessResult(CommandAccessStatus.ALLOWED)
