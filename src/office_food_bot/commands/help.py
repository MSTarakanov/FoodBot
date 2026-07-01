from __future__ import annotations

from aiogram.types import Message

from office_food_bot.commands.definitions import HELP_TEXT


async def help_command(message: Message) -> None:
    await message.answer(HELP_TEXT)
