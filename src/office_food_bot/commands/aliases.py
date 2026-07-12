from __future__ import annotations

from aiogram.filters import Filter
from aiogram.types import Message

from office_food_bot.commands.definitions import command_definition
from office_food_bot.commands.parsing import ParsedCommand, parse_command


class CommandAliasFilter(Filter):
    def __init__(self, canonical_name: str) -> None:
        self._canonical_name = canonical_name

    async def __call__(self, message: Message) -> dict[str, ParsedCommand]:
        parsed_command = parse_command(message.text)
        if parsed_command is None:
            return {}

        definition = command_definition(parsed_command.name)
        if definition is None or definition.name != self._canonical_name:
            return {}
        if parsed_command.name == definition.name:
            return {}

        return {"alias_command": parsed_command}
