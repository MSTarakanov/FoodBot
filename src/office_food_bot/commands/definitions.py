from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandDefinition:
    name: str
    description: str
    usage: str
    admin_only: bool = False


COMMANDS: tuple[CommandDefinition, ...] = (
    CommandDefinition("start", "показать приветствие", "/start"),
    CommandDefinition("help", "показать список команд", "/help"),
    CommandDefinition("hi", "проверить, что бот на месте", "/hi"),
    CommandDefinition("register", "зарегистрироваться по имени", "/register Максим"),
    CommandDefinition("cancel", "отменить текущий сценарий", "/cancel"),
    CommandDefinition(
        "approve",
        "подтвердить регистрацию",
        "/approve 123456789",
        admin_only=True,
    ),
    CommandDefinition(
        "register_requests_list",
        "показать заявки на регистрацию",
        "/register_requests_list",
        admin_only=True,
    ),
    CommandDefinition("meta", "сообщить, через сколько минут придешь", "/meta 25"),
    CommandDefinition("balance", "показать баланс Splitwise", "/balance"),
)

START_TEXT = "Привет! Я офисный бот про еду. Напиши /help, чтобы увидеть команды."


def visible_commands(*, is_admin: bool) -> tuple[CommandDefinition, ...]:
    return tuple(
        definition
        for definition in COMMANDS
        if is_admin or not definition.admin_only
    )


PUBLIC_COMMANDS = visible_commands(is_admin=False)
ADMIN_COMMANDS = visible_commands(is_admin=True)


def help_text(*, is_admin: bool) -> str:
    return "Команды:\n" + "\n".join(
        f"{definition.usage} - {definition.description}"
        for definition in visible_commands(is_admin=is_admin)
    )


PUBLIC_HELP_TEXT = help_text(is_admin=False)
ADMIN_HELP_TEXT = help_text(is_admin=True)
