from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    NoArguments,
    NoArgumentsParser,
)
from office_food_bot.commanding.definition import (
    START_TEXT,
    CommandDefinition,
    CommandScope,
    HelpSection,
)
from office_food_bot.messaging import BotMessenger


class StartCommand(EffectCommand[NoArguments]):
    definition = CommandDefinition(
        "start",
        "показать приветствие",
        "/start",
        CommandScope.PRIVATE,
        HelpSection.SERVICE,
    )

    def __init__(self, messenger: BotMessenger) -> None:
        super().__init__(messenger, NoArgumentsParser(), (), ())

    async def execute_effect(
        self,
        context: CommandContext,
        request: NoArguments,
    ) -> None:
        del request
        await self._messenger.reply(context.message, START_TEXT)
