from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from office_food_bot.commanding.definition import (
    CommandDefinition,
    CommandHelpEntry,
    CommandScope,
    VisibleCommandHelpEntry,
)
from office_food_bot.commanding.errors.models import CommonError, CommonErrorCode
from office_food_bot.services.debug import DebugService
from office_food_bot.services.registration import RegistrationService

PRIVATE_CHAT_TYPE = "private"
GROUP_CHAT_TYPES = frozenset({"group", "supergroup"})


class CommandAccessDenialReason(StrEnum):
    PRIVATE_ONLY = "private_only"
    GROUP_ONLY = "group_only"
    ADMIN_ONLY = "admin_only"


@dataclass(frozen=True)
class CommandAccessResult:
    denial_reason: CommandAccessDenialReason | None = None

    @property
    def allowed(self) -> bool:
        return self.denial_reason is None


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
        definition: CommandDefinition,
        chat_type: str,
        telegram_user_id: int | None,
        arguments: str | None = None,
    ) -> CommandAccessResult:
        denial = self._scope_denial(
            definition.scope_for(arguments),
            chat_type,
            telegram_user_id,
        )
        if denial is not None:
            return _denied(denial)

        if definition.admin_only and not self.is_admin(telegram_user_id):
            return _denied(CommandAccessDenialReason.ADMIN_ONLY)

        return _allowed()

    def validate_run(
        self,
        definition: CommandDefinition,
        chat_type: str,
        telegram_user_id: int | None,
        arguments: str | None = None,
    ) -> None:
        denial = self.can_run(
            definition,
            chat_type,
            telegram_user_id,
            arguments,
        ).denial_reason
        if denial is not None:
            raise CommonError(_common_error_code(denial))

    def visible_commands(
        self,
        definitions: Iterable[CommandDefinition],
        chat_type: str,
        telegram_user_id: int | None,
    ) -> tuple[CommandDefinition, ...]:
        return tuple(
            definition
            for definition in definitions
            if definition.show_in_menu
            and self._definition_visible(definition, chat_type, telegram_user_id)
        )

    def visible_help_entries(
        self,
        definitions: Iterable[CommandDefinition],
        chat_type: str,
        telegram_user_id: int | None,
    ) -> tuple[VisibleCommandHelpEntry, ...]:
        return tuple(
            self._visible_help_entry(definition, entry)
            for definition in definitions
            if not definition.admin_only or self.is_admin(telegram_user_id)
            for entry in self._help_entries(definition)
            if self._scope_denial(
                entry.scope or definition.scope,
                chat_type,
                telegram_user_id,
            )
            is None
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

    def can_run_group_command_in_chat(
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

    def _definition_visible(
        self,
        definition: CommandDefinition,
        chat_type: str,
        telegram_user_id: int | None,
    ) -> bool:
        if definition.admin_only and not self.is_admin(telegram_user_id):
            return False
        scopes = {definition.scope, *(item.scope for item in definition.scope_overrides)}
        return any(
            self._scope_denial(scope, chat_type, telegram_user_id) is None for scope in scopes
        )

    def _scope_denial(
        self,
        scope: CommandScope,
        chat_type: str,
        telegram_user_id: int | None,
    ) -> CommandAccessDenialReason | None:
        if scope == CommandScope.PRIVATE and chat_type != PRIVATE_CHAT_TYPE:
            return CommandAccessDenialReason.PRIVATE_ONLY
        if scope == CommandScope.GROUP and not self.can_run_group_command_in_chat(
            chat_type, telegram_user_id
        ):
            return CommandAccessDenialReason.GROUP_ONLY
        return None

    def _help_entries(
        self,
        definition: CommandDefinition,
    ) -> tuple[CommandHelpEntry, ...]:
        primary = CommandHelpEntry(
            definition.usage,
            definition.description,
            definition.help_section,
            definition.scope,
        )
        return (primary, *definition.additional_help)

    def _visible_help_entry(
        self,
        definition: CommandDefinition,
        entry: CommandHelpEntry,
    ) -> VisibleCommandHelpEntry:
        return VisibleCommandHelpEntry(
            command_name=definition.name,
            text_aliases=definition.text_aliases,
            usage=entry.usage,
            description=entry.description,
            section=entry.section,
        )


def _allowed() -> CommandAccessResult:
    return CommandAccessResult()


def _denied(reason: CommandAccessDenialReason) -> CommandAccessResult:
    return CommandAccessResult(reason)


def _common_error_code(reason: CommandAccessDenialReason) -> CommonErrorCode:
    if reason == CommandAccessDenialReason.PRIVATE_ONLY:
        return CommonErrorCode.PRIVATE_CHAT_REQUIRED
    if reason == CommandAccessDenialReason.GROUP_ONLY:
        return CommonErrorCode.GROUP_CHAT_REQUIRED
    if reason == CommandAccessDenialReason.ADMIN_ONLY:
        return CommonErrorCode.ADMIN_REQUIRED
    raise ValueError(f"Unsupported command access denial: {reason}")
