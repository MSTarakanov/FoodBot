from __future__ import annotations

from aiogram.filters.command import CommandObject
from aiogram.types import Message

from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.services import BotServices


async def meta_command(
    message: Message,
    command: CommandObject,
    services: BotServices,
) -> None:
    profile = telegram_profile_from_message(message)
    if profile is None:
        await message.answer("Не вижу твой Telegram user id.")
        return

    if not command.args:
        await message.answer("Напиши через сколько минут: /meta 25")
        return

    await message.answer(services.presence.meta(profile.telegram_user_id, command.args))
