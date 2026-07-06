from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class CommandScope(StrEnum):
    ANY = "any"
    PRIVATE = "private"
    GROUP = "group"


@dataclass(frozen=True)
class CommandDefinition:
    name: str
    description: str
    usage: str
    scope: CommandScope
    admin_only: bool = False


COMMANDS: tuple[CommandDefinition, ...] = (
    CommandDefinition("start", "показать приветствие", "/start", CommandScope.PRIVATE),
    CommandDefinition("help", "показать список команд", "/help", CommandScope.ANY),
    CommandDefinition("hi", "проверить, что бот на месте", "/hi", CommandScope.ANY),
    CommandDefinition("register", "пройти регистрацию", "/register", CommandScope.PRIVATE),
    CommandDefinition(
        "request_register",
        "попросить админа зарегистрировать вас",
        "/request_register",
        CommandScope.PRIVATE,
    ),
    CommandDefinition("quit", "отрегистрироваться", "/quit", CommandScope.PRIVATE),
    CommandDefinition("cancel", "отменить текущий сценарий", "/cancel", CommandScope.PRIVATE),
    CommandDefinition(
        "approve",
        "подтвердить регистрацию",
        "/approve 123456789",
        CommandScope.PRIVATE,
        admin_only=True,
    ),
    CommandDefinition(
        "register_requests_list",
        "показать заявки на регистрацию",
        "/register_requests_list",
        CommandScope.PRIVATE,
        admin_only=True,
    ),
    CommandDefinition(
        "debug",
        "включить или выключить debug режим",
        "/debug 1",
        CommandScope.PRIVATE,
        admin_only=True,
    ),
    CommandDefinition(
        "meta",
        "сообщить, через сколько минут или в каком диапазоне придешь",
        "/meta 25 или /meta 20-30",
        CommandScope.GROUP,
    ),
    CommandDefinition(
        "eta",
        "сообщить ожидаемое время доставки",
        "/eta 20 или /eta 20-30",
        CommandScope.GROUP,
    ),
    CommandDefinition("balance", "показать баланс Splitwise", "/balance", CommandScope.ANY),
    CommandDefinition("lunch", "создать опрос про обед", "/lunch", CommandScope.GROUP),
    CommandDefinition(
        "lunch_auto_on",
        "включить авто-ланч в этом чате",
        "/lunch_auto_on",
        CommandScope.GROUP,
        admin_only=True,
    ),
    CommandDefinition(
        "lunch_auto_off",
        "выключить авто-ланч в этом чате",
        "/lunch_auto_off",
        CommandScope.GROUP,
        admin_only=True,
    ),
    CommandDefinition(
        "lunch_auto_status",
        "показать статус авто-ланча",
        "/lunch_auto_status",
        CommandScope.GROUP,
        admin_only=True,
    ),
)

START_TEXT = "Привет! Я офисный бот про еду. Напиши /help, чтобы увидеть команды."


def command_definition(name: str) -> CommandDefinition | None:
    return next((definition for definition in COMMANDS if definition.name == name), None)


def help_text(definitions: Iterable[CommandDefinition]) -> str:
    return "Команды:\n" + "\n".join(
        f"{definition.usage} - {definition.description}"
        for definition in definitions
    )
