from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    RawArguments,
    RawArgumentsParser,
)
from office_food_bot.commanding.definition import CommandDefinition, CommandScope, HelpSection
from office_food_bot.controllers.registration import quit_command
from office_food_bot.services import BotServices


class QuitCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "quit",
        "отрегистрироваться",
        "/quit",
        CommandScope.PRIVATE,
        HelpSection.PROFILE_SETTINGS,
    )

    def __init__(self, services: BotServices) -> None:
        super().__init__(RawArgumentsParser(), (), ())
        self._services = services

    async def execute_effect(
        self,
        context: CommandContext,
        request: RawArguments,
    ) -> None:
        await quit_command(
            context.message,
            context.messenger,
            self._services,
            context.state,
        )
