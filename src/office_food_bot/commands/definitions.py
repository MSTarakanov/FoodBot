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


@dataclass(frozen=True)
class CommandHelpEntry:
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
        CommandScope.PRIVATE,
        HelpSection.PROFILE_SETTINGS,
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
        "отметить отпуск",
        "/vacation 2",
        CommandScope.GROUP,
        HelpSection.PROFILE_SETTINGS,
    ),
    CommandDefinition(
        "lunch",
        "создать опрос про обед",
        "/lunch [rose|роза|skyline|скайлайн]",
        CommandScope.GROUP,
        HelpSection.MAIN,
    ),
    CommandDefinition(
        "coffee",
        "позвать на кофе",
        "/coffee 15 или /coffee 16:30",
        CommandScope.GROUP,
        HelpSection.MAIN,
        additional_help=(
            CommandHelpEntry(
                "/coffee on",
                "включить приглашения",
                HelpSection.PROFILE_SETTINGS,
            ),
            CommandHelpEntry(
                "/coffee off",
                "выключить приглашения",
                HelpSection.PROFILE_SETTINGS,
            ),
        ),
        text_aliases=("кофе",),
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
