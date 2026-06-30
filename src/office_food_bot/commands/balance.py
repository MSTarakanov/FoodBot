from __future__ import annotations

from aiogram.types import Message

from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.services import BotServices


async def balance_command(message: Message, services: BotServices) -> None:
    profile = telegram_profile_from_message(message)
    if profile is None:
        await message.answer("Не вижу твой Telegram user id.")
        return

    await message.answer(services.balances.balance(profile.telegram_user_id))
