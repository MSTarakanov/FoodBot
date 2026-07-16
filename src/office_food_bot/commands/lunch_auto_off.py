from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    IdentityResolver,
    NoArguments,
    NoArgumentsParser,
)
from office_food_bot.commanding.definition import CommandDefinition, CommandScope, HelpSection
from office_food_bot.commanding.errors.models import CommonErrorCode
from office_food_bot.commanding.errors.rendering import ErrorRenderer
from office_food_bot.messaging import BotMessenger
from office_food_bot.services.lunch_auto import LunchAutoChatService


class LunchAutoOffCommand(EffectCommand[NoArguments, NoArguments]):
    definition = CommandDefinition(
        "lunch_auto_off",
        "выключить авто-ланч в этом чате",
        "/lunch_auto_off",
        CommandScope.GROUP,
        HelpSection.AUTOMATION,
        admin_only=True,
    )

    def __init__(
        self,
        messenger: BotMessenger,
        common_error_renderer: ErrorRenderer[CommonErrorCode],
        lunch_auto_chats: LunchAutoChatService,
    ) -> None:
        super().__init__(
            messenger,
            common_error_renderer,
            NoArgumentsParser(),
            (),
            (),
            IdentityResolver(),
        )
        self._lunch_auto_chats = lunch_auto_chats

    async def execute_effect(
        self,
        context: CommandContext,
        _request: NoArguments,
    ) -> None:
        self._lunch_auto_chats.disable(context.message.chat.id)
        await self._messenger.reply(
            context.message,
            "Авто-ланч выключен для этого чата.",
        )
