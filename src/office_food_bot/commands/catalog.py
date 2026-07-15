from __future__ import annotations

from collections.abc import Iterable

from office_food_bot.commands.base import Command
from office_food_bot.commands.definitions import CommandDefinition


class CommandCatalog:
    def __init__(self, commands: Iterable[Command]) -> None:
        command_list = tuple(commands)
        if not command_list:
            raise ValueError("At least one command must be registered")

        commands_by_name: dict[str, Command] = {}
        for command in command_list:
            for name in (command.definition.name, *command.definition.text_aliases):
                normalized_name = name.casefold()
                if normalized_name in commands_by_name:
                    raise ValueError(f"Duplicate command name or alias: {name}")
                commands_by_name[normalized_name] = command

        self._commands = command_list
        self._commands_by_name = commands_by_name

    @property
    def commands(self) -> tuple[Command, ...]:
        return self._commands

    @property
    def definitions(self) -> tuple[CommandDefinition, ...]:
        return tuple(command.definition for command in self._commands)

    @property
    def invocation_names(self) -> tuple[str, ...]:
        return tuple(self._commands_by_name)

    def resolve(self, raw_name: str) -> Command | None:
        return self._commands_by_name.get(raw_name.casefold())
