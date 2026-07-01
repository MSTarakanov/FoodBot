from __future__ import annotations

from aiogram import Bot
from aiogram.types import BotCommand

from office_food_bot.commands.definitions import COMMANDS


async def setup_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command=definition.name, description=definition.description)
            for definition in COMMANDS
        ]
    )
