from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    RawArguments,
    RawArgumentsParser,
)
from office_food_bot.commanding.definition import CommandDefinition, CommandScope, HelpSection
from office_food_bot.previews import MESSAGE_PREVIEWS


class TestCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "test",
        "отправить тестовое сообщение",
        "/test balance-full",
        CommandScope.PRIVATE,
        HelpSection.ADMINISTRATION,
        admin_only=True,
        show_in_menu=False,
    )

    def __init__(self) -> None:
        super().__init__(RawArgumentsParser(), (), ())

    async def execute_effect(
        self,
        context: CommandContext,
        request: RawArguments,
    ) -> None:
        await context.state.clear()
        payload = MESSAGE_PREVIEWS.render(request.value or "")
        if payload is None:
            await context.messenger.reply(
                context.message,
                MESSAGE_PREVIEWS.help_text(),
            )
            return

        await context.messenger.reply_payload(context.message, payload)
