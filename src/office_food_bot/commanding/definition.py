from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from office_food_bot.commanding.errors.models import InputErrorCode


class CommandScope(StrEnum):
    ANY = "any"
    PRIVATE = "private"
    GROUP = "group"


class CommandFlowPolicy(StrEnum):
    RESET_BEFORE_RUN = "reset_before_run"
    MANAGED_BY_COMMAND = "managed_by_command"


class HelpSection(StrEnum):
    MAIN = "Основные"
    PROFILE_SETTINGS = "Профиль и настройки"
    AUTOMATION = "Автоматизация"
    ADMINISTRATION = "Администрирование"
    SERVICE = "Служебные"


class CommandArgumentPattern(StrEnum):
    EMPTY = "empty"
    TOGGLE = "toggle"

    def matches(self, arguments: str | None) -> bool:
        normalized = (arguments or "").strip().casefold()
        if self == CommandArgumentPattern.EMPTY:
            return not normalized
        return normalized in {"on", "off"}


@dataclass(frozen=True)
class CommandScopeOverride:
    pattern: CommandArgumentPattern
    scope: CommandScope


@dataclass(frozen=True)
class CommandInputMessage:
    code: InputErrorCode
    text: str


@dataclass(frozen=True)
class CommandHelpEntry:
    usage: str
    description: str
    section: HelpSection
    scope: CommandScope | None = None


@dataclass(frozen=True)
class VisibleCommandHelpEntry:
    command_name: str
    text_aliases: tuple[str, ...]
    usage: str
    description: str
    section: HelpSection


@dataclass(frozen=True)
class CommandDefinition:
    name: str
    description: str
    usage: str
    scope: CommandScope
    help_section: HelpSection
    admin_only: bool = False
    additional_help: tuple[CommandHelpEntry, ...] = ()
    text_aliases: tuple[str, ...] = ()
    scope_overrides: tuple[CommandScopeOverride, ...] = ()
    show_in_menu: bool = True
    private_description: str | None = None
    flow_policy: CommandFlowPolicy = CommandFlowPolicy.RESET_BEFORE_RUN
    input_errors: tuple[CommandInputMessage, ...] = ()

    def scope_for(self, arguments: str | None) -> CommandScope:
        override = next(
            (
                item
                for item in self.scope_overrides
                if item.pattern.matches(arguments)
            ),
            None,
        )
        if override is None:
            return self.scope
        return override.scope

    def menu_description(self, chat_type: str) -> str:
        if chat_type == "private" and self.private_description is not None:
            return self.private_description
        return self.description

    def input_error_text(self, code: InputErrorCode) -> str:
        match = next((item for item in self.input_errors if item.code == code), None)
        if match is None:
            raise RuntimeError(
                f"Command /{self.name} has no message for input error {code.value}"
            )
        return match.text


START_TEXT = "Привет! Я офисный бот про еду. Напиши /help, чтобы увидеть команды."
