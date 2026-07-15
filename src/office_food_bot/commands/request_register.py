from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    RawArguments,
    RawArgumentsParser,
)
from office_food_bot.commanding.definition import CommandDefinition, CommandScope, HelpSection
from office_food_bot.controllers.registration import request_register_command
from office_food_bot.services import BotServices


class RequestRegisterCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "request_register",
        "попросить админа зарегистрировать вас",
        "/request_register",
        CommandScope.ANY,
        HelpSection.PROFILE_SETTINGS,
        show_in_menu=False,
    )

    def __init__(self, services: BotServices) -> None:
        super().__init__(RawArgumentsParser(), (), ())
        self._services = services

    async def execute_effect(
        self,
        context: CommandContext,
        request: RawArguments,
    ) -> None:
        await request_register_command(
            context.message,
            context.bot,
            context.messenger,
            self._services,
            context.state,
        )
