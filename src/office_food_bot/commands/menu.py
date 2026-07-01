from __future__ import annotations

from collections.abc import Iterable

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat

from office_food_bot.commands.definitions import ADMIN_COMMANDS, PUBLIC_COMMANDS, CommandDefinition


async def setup_bot_commands(bot: Bot, admin_ids: Iterable[int]) -> None:
    await bot.set_my_commands(_bot_commands(PUBLIC_COMMANDS))

    for admin_id in sorted(admin_ids):
        await bot.set_my_commands(
            _bot_commands(ADMIN_COMMANDS),
            scope=BotCommandScopeChat(chat_id=admin_id),
        )


def _bot_commands(definitions: Iterable[CommandDefinition]) -> list[BotCommand]:
    return [
        BotCommand(command=definition.name, description=definition.description)
        for definition in definitions
    ]
