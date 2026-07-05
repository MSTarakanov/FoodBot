from __future__ import annotations

from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices


async def eta_command(
    message: Message,
    command: CommandObject,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    await state.clear()
    profile = telegram_profile_from_message(message)
    if profile is None:
        await messenger.reply(message, "Не вижу твой Telegram user id.")
        return

    command_name = command.command
    if not command.args:
        await messenger.reply(
            message,
            services.presence.eta_missing_minutes_reply(command_name),
        )
        return

    await messenger.reply(
        message,
        services.presence.eta(profile.telegram_user_id, command.args, command_name),
    )
