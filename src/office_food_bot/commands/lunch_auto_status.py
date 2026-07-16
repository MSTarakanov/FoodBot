from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    NoArguments,
    NoArgumentsParser,
)
from office_food_bot.commanding.definition import CommandDefinition, CommandScope, HelpSection
from office_food_bot.commanding.errors.models import CommonErrorCode
from office_food_bot.commanding.errors.rendering import ErrorRenderer
from office_food_bot.messaging import BotMessenger
from office_food_bot.services.lunch_auto import LunchAutoChatService


class LunchAutoStatusCommand(EffectCommand[NoArguments]):
    definition = CommandDefinition(
        "lunch_auto_status",
        "показать статус авто-ланча",
        "/lunch_auto_status",
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
        super().__init__(messenger, common_error_renderer, NoArgumentsParser(), (), ())
        self._lunch_auto_chats = lunch_auto_chats

    async def execute_effect(
        self,
        context: CommandContext,
        request: NoArguments,
    ) -> None:
        del request
        await self._messenger.reply(
            context.message,
            (
                "Авто-ланч включен для этого чата."
                if self._lunch_auto_chats.is_enabled(context.message.chat.id)
                else "Авто-ланч выключен для этого чата."
            ),
        )
