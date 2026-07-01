from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandDefinition:
    name: str
    description: str
    usage: str


COMMANDS: tuple[CommandDefinition, ...] = (
    CommandDefinition("start", "показать приветствие", "/start"),
    CommandDefinition("help", "показать список команд", "/help"),
    CommandDefinition("hi", "проверить, что бот на месте", "/hi"),
    CommandDefinition("register", "зарегистрироваться по имени", "/register Максим"),
    CommandDefinition("approve", "подтвердить регистрацию", "/approve 123456789"),
    CommandDefinition("meta", "сообщить, через сколько минут придешь", "/meta 25"),
    CommandDefinition("balance", "показать баланс Splitwise", "/balance"),
)

START_TEXT = "Привет! Я офисный бот про еду. Напиши /help, чтобы увидеть команды."

HELP_TEXT = "Команды:\n" + "\n".join(
    f"{definition.usage} - {definition.description}" for definition in COMMANDS
)
