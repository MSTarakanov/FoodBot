from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    IdentityResolver,
    NoArguments,
    NoArgumentsParser,
)
from office_food_bot.commanding.definition import (
    START_TEXT,
    CommandDefinition,
    CommandScope,
    HelpSection,
)
from office_food_bot.commanding.errors.models import CommonErrorCode
from office_food_bot.commanding.errors.rendering import ErrorRenderer
from office_food_bot.messaging import BotMessenger


class StartCommand(EffectCommand[NoArguments, NoArguments]):
    definition = CommandDefinition(
        "start",
        "показать приветствие",
        "/start",
        CommandScope.PRIVATE,
        HelpSection.SERVICE,
    )

    def __init__(
        self,
        messenger: BotMessenger,
        common_error_renderer: ErrorRenderer[CommonErrorCode],
    ) -> None:
        super().__init__(
            messenger,
            common_error_renderer,
            NoArgumentsParser(),
            (),
            (),
            IdentityResolver(),
        )

    async def execute_effect(
        self,
        context: CommandContext,
        _request: NoArguments,
    ) -> None:
        await self._messenger.reply(context.message, START_TEXT)
