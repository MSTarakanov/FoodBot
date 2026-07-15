from __future__ import annotations

from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

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
