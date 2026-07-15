from __future__ import annotations

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commands.base import (
    CommandContext,
    EffectCommand,
    RawArguments,
    RawArgumentsParser,
)
from office_food_bot.commands.definitions import (
    START_TEXT,
    CommandDefinition,
    CommandScope,
    HelpSection,
)
from office_food_bot.messaging import BotMessenger


async def start_command(
    message: Message,
    messenger: BotMessenger,
    state: FSMContext,
) -> None:
    await state.clear()
    await messenger.reply(message, START_TEXT)


class StartCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "start",
        "показать приветствие",
        "/start",
        CommandScope.PRIVATE,
        HelpSection.SERVICE,
    )

    def __init__(self) -> None:
        super().__init__(RawArgumentsParser(), (), ())

    async def execute_effect(
        self,
        context: CommandContext,
        request: RawArguments,
    ) -> None:
        await start_command(context.message, context.messenger, context.state)
