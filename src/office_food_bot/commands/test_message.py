from __future__ import annotations

from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commands.base import (
    CommandContext,
    EffectCommand,
    RawArguments,
    RawArgumentsParser,
)
from office_food_bot.commands.definitions import CommandDefinition, CommandScope, HelpSection
from office_food_bot.messaging import BotMessenger
from office_food_bot.previews import MESSAGE_PREVIEWS


async def test_message_command(
    message: Message,
    command: CommandObject,
    messenger: BotMessenger,
    state: FSMContext,
) -> None:
    await state.clear()
    payload = MESSAGE_PREVIEWS.render(command.args or "")
    if payload is None:
        await messenger.reply(message, MESSAGE_PREVIEWS.help_text())
        return

    await messenger.reply_payload(message, payload)


class TestMessageCommand(EffectCommand[RawArguments]):
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
        command = CommandObject(command=context.invocation.name, args=request.value)
        await test_message_command(
            context.message,
            command,
            context.messenger,
            context.state,
        )
