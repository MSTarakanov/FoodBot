from __future__ import annotations

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.messaging import BotMessenger


async def hi_command(
    message: Message,
    messenger: BotMessenger,
    state: FSMContext,
) -> None:
    await state.clear()
    await messenger.reply(message, "Привет! Я на месте.")
