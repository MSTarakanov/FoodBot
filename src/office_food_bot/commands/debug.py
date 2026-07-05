from __future__ import annotations

from aiogram import Bot
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commands.access import ensure_command_allowed
from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.commands.menu import setup_private_admin_commands
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices

DEBUG_ON_VALUES = frozenset({"1", "on", "true", "вкл"})
DEBUG_OFF_VALUES = frozenset({"0", "off", "false", "выкл"})


async def debug_command(
    message: Message,
    command: CommandObject,
    bot: Bot,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    if not await ensure_command_allowed(message, "debug", messenger, services, state):
        return

    await state.clear()
    profile = telegram_profile_from_message(message)
    if profile is None:
        await messenger.reply(message, "Не вижу твой Telegram user id.")
        return

    raw_argument = (command.args or "").strip().casefold()
    if not raw_argument:
        await messenger.reply(
            message,
            _debug_status_text(services.debug.is_enabled(profile.telegram_user_id)),
        )
        return

    if raw_argument in DEBUG_ON_VALUES:
        services.debug.set_enabled(profile.telegram_user_id, True)
        await setup_private_admin_commands(
            bot,
            services.command_access,
            profile.telegram_user_id,
        )
        await messenger.reply(message, "Debug включен. В личке доступны все команды.")
        return

    if raw_argument in DEBUG_OFF_VALUES:
        services.debug.set_enabled(profile.telegram_user_id, False)
        await setup_private_admin_commands(
            bot,
            services.command_access,
            profile.telegram_user_id,
        )
        await messenger.reply(message, "Debug выключен.")
        return

    await messenger.reply(message, "Напиши /debug 1 или /debug 0")


def _debug_status_text(enabled: bool) -> str:
    if enabled:
        return "Debug: включен."
    return "Debug: выключен."
