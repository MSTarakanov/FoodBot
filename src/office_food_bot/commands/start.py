from __future__ import annotations

from aiogram.types import Message

from office_food_bot.commands.definitions import START_TEXT


async def start_command(message: Message) -> None:
    await message.answer(START_TEXT)
