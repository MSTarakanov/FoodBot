from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    BotCommandScopeDefault,
    BotCommandScopeUnion,
)

from office_food_bot.commands.definitions import CommandDefinition

PRIVATE_CHAT_TYPE = "private"
GROUP_MENU_CHAT_TYPE = "group"


class BotCommandClient(Protocol):
    async def set_my_commands(
        self,
        commands: list[BotCommand],
        scope: BotCommandScopeUnion | None = None,
    ) -> bool: ...


class CommandAccess(Protocol):
    def visible_commands(
        self,
        chat_type: str,
        telegram_user_id: int | None,
    ) -> tuple[CommandDefinition, ...]: ...

    def admin_chat_ids_for_menu(self) -> tuple[int, ...]: ...


async def setup_bot_commands(
    bot: BotCommandClient,
    access: CommandAccess,
) -> None:
    await bot.set_my_commands(
        _bot_commands(access.visible_commands(PRIVATE_CHAT_TYPE, None)),
        scope=BotCommandScopeDefault(),
    )
    await bot.set_my_commands(
        _bot_commands(access.visible_commands(PRIVATE_CHAT_TYPE, None)),
        scope=BotCommandScopeAllPrivateChats(),
    )
    await bot.set_my_commands(
        _bot_commands(access.visible_commands(GROUP_MENU_CHAT_TYPE, None)),
        scope=BotCommandScopeAllGroupChats(),
    )

    for admin_id in access.admin_chat_ids_for_menu():
        await setup_private_admin_commands(bot, access, admin_id)


async def setup_private_admin_commands(
    bot: BotCommandClient,
    access: CommandAccess,
    admin_id: int,
) -> None:
    try:
        await bot.set_my_commands(
            _bot_commands(access.visible_commands(PRIVATE_CHAT_TYPE, admin_id)),
            scope=BotCommandScopeChat(chat_id=admin_id),
        )
    except TelegramBadRequest as error:
        if "chat not found" not in str(error):
            raise


def _bot_commands(definitions: Iterable[CommandDefinition]) -> list[BotCommand]:
    return [
        BotCommand(command=definition.name, description=definition.description)
        for definition in definitions
    ]
