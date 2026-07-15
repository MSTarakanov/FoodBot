from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CommandScope(StrEnum):
    ANY = "any"
    PRIVATE = "private"
    GROUP = "group"


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


COMMANDS: tuple[CommandDefinition, ...] = (
    CommandDefinition(
        "start",
        "показать приветствие",
        "/start",
        CommandScope.PRIVATE,
        HelpSection.SERVICE,
    ),
    CommandDefinition(
        "help",
        "показать список команд",
        "/help",
        CommandScope.ANY,
        HelpSection.SERVICE,
    ),
    CommandDefinition(
        "hi",
        "проверить, что бот на месте",
        "/hi",
        CommandScope.ANY,
        HelpSection.SERVICE,
    ),
    CommandDefinition(
        "register",
        "пройти регистрацию",
        "/register",
        CommandScope.PRIVATE,
        HelpSection.PROFILE_SETTINGS,
    ),
    CommandDefinition(
        "request_register",
        "попросить админа зарегистрировать вас",
        "/request_register",
        CommandScope.ANY,
        HelpSection.PROFILE_SETTINGS,
        show_in_menu=False,
    ),
    CommandDefinition(
        "quit",
        "отрегистрироваться",
        "/quit",
        CommandScope.PRIVATE,
        HelpSection.PROFILE_SETTINGS,
    ),
    CommandDefinition(
        "cancel",
        "отменить текущий сценарий",
        "/cancel",
        CommandScope.PRIVATE,
        HelpSection.SERVICE,
    ),
    CommandDefinition(
        "approve",
        "подтвердить регистрацию",
        "/approve 123456789",
        CommandScope.PRIVATE,
        HelpSection.ADMINISTRATION,
        admin_only=True,
    ),
    CommandDefinition(
        "register_requests_list",
        "показать заявки на регистрацию",
        "/register_requests_list",
        CommandScope.PRIVATE,
        HelpSection.ADMINISTRATION,
        admin_only=True,
    ),
    CommandDefinition(
        "debug",
        "включить или выключить debug режим",
        "/debug 1",
        CommandScope.PRIVATE,
        HelpSection.ADMINISTRATION,
        admin_only=True,
    ),
    CommandDefinition(
        "test",
        "отправить тестовое сообщение",
        "/test balance-full",
        CommandScope.PRIVATE,
        HelpSection.ADMINISTRATION,
        admin_only=True,
        show_in_menu=False,
    ),
    CommandDefinition(
        "meta",
        "сообщить, через сколько минут или в каком диапазоне придешь",
        "/meta 25 или /meta 20-30",
        CommandScope.GROUP,
        HelpSection.MAIN,
    ),
    CommandDefinition(
        "eta",
        "сообщить ожидаемое время доставки",
        "/eta 20 или /eta 20-30",
        CommandScope.GROUP,
        HelpSection.MAIN,
    ),
    CommandDefinition(
        "balance",
        "показать баланс Splitwise",
        "/balance",
        CommandScope.ANY,
        HelpSection.MAIN,
    ),
    CommandDefinition(
        "vacation",
        "показать статус отпуска",
        "/vacation",
        CommandScope.GROUP,
        HelpSection.PROFILE_SETTINGS,
        additional_help=(
            CommandHelpEntry(
                "/vacation 2 или /vacation 20.07",
                "уйти в отпуск",
                HelpSection.PROFILE_SETTINGS,
            ),
            CommandHelpEntry(
                "/vacation 0 или /vacation off",
                "выйти из отпуска",
                HelpSection.PROFILE_SETTINGS,
            ),
        ),
    ),
    CommandDefinition(
        "lunch",
        "создать опрос про обед",
        "/lunch [rose|роза|skyline|скайлайн]",
        CommandScope.GROUP,
        HelpSection.MAIN,
        additional_help=(
            CommandHelpEntry(
                "/lunch",
                "показать настройки приглашений на ланч",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.PRIVATE,
            ),
            CommandHelpEntry(
                "/lunch on",
                "включить приглашения",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.ANY,
            ),
            CommandHelpEntry(
                "/lunch off",
                "выключить приглашения",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.ANY,
            ),
        ),
        scope_overrides=(
            CommandScopeOverride(CommandArgumentPattern.EMPTY, CommandScope.ANY),
            CommandScopeOverride(CommandArgumentPattern.TOGGLE, CommandScope.ANY),
        ),
        private_description="настроить приглашения на ланч",
    ),
    CommandDefinition(
        "coffee",
        "позвать на кофе",
        "/coffee 15 или /coffee 16:30",
        CommandScope.GROUP,
        HelpSection.MAIN,
        additional_help=(
            CommandHelpEntry(
                "/coffee",
                "показать настройки приглашений на кофе",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.PRIVATE,
            ),
            CommandHelpEntry(
                "/coffee on",
                "включить приглашения",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.ANY,
            ),
            CommandHelpEntry(
                "/coffee off",
                "выключить приглашения",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.ANY,
            ),
        ),
        text_aliases=("кофе",),
        scope_overrides=(
            CommandScopeOverride(CommandArgumentPattern.EMPTY, CommandScope.ANY),
            CommandScopeOverride(CommandArgumentPattern.TOGGLE, CommandScope.ANY),
        ),
        private_description="настроить приглашения на кофе",
    ),
    CommandDefinition(
        "lunch_auto_on",
        "включить авто-ланч в этом чате",
        "/lunch_auto_on",
        CommandScope.GROUP,
        HelpSection.AUTOMATION,
        admin_only=True,
    ),
    CommandDefinition(
        "lunch_auto_off",
        "выключить авто-ланч в этом чате",
        "/lunch_auto_off",
        CommandScope.GROUP,
        HelpSection.AUTOMATION,
        admin_only=True,
    ),
    CommandDefinition(
        "lunch_auto_status",
        "показать статус авто-ланча",
        "/lunch_auto_status",
        CommandScope.GROUP,
        HelpSection.AUTOMATION,
        admin_only=True,
    ),
)

START_TEXT = "Привет! Я офисный бот про еду. Напиши /help, чтобы увидеть команды."


def command_definition(name: str) -> CommandDefinition | None:
    normalized_name = name.casefold()
    return next(
        (
            definition
            for definition in COMMANDS
            if normalized_name == definition.name
            or any(
                normalized_name == alias.casefold()
                for alias in definition.text_aliases
            )
        ),
        None,
    )
