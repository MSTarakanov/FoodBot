from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiogram import Router

    from office_food_bot.commands.menu import BotCommandClient, CommandAccess

__all__ = ["create_command_router", "setup_bot_commands"]


def create_command_router() -> Router:
    from office_food_bot.commands.router import create_command_router as create_router

    return create_router()


async def setup_bot_commands(
    bot: BotCommandClient,
    access: CommandAccess,
    admin_ids: Iterable[int],
) -> None:
    from office_food_bot.commands.menu import setup_bot_commands as setup_menu

    await setup_menu(bot, access, admin_ids)
