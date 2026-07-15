from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    RawArguments,
    RawArgumentsParser,
)
from office_food_bot.commanding.definition import CommandDefinition, CommandScope, HelpSection
from office_food_bot.controllers.lunch_auto import enable_lunch_auto
from office_food_bot.services import BotServices


class LunchAutoOnCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "lunch_auto_on",
        "включить авто-ланч в этом чате",
        "/lunch_auto_on",
        CommandScope.GROUP,
        HelpSection.AUTOMATION,
        admin_only=True,
    )

    def __init__(self, services: BotServices) -> None:
        super().__init__(RawArgumentsParser(), (), ())
        self._services = services

    async def execute_effect(
        self,
        context: CommandContext,
        request: RawArguments,
    ) -> None:
        await enable_lunch_auto(context, self._services)
