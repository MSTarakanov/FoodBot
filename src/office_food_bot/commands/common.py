from __future__ import annotations

from aiogram.types import Message

from office_food_bot.models import TelegramProfile


def telegram_profile_from_message(message: Message) -> TelegramProfile | None:
    if message.from_user is None:
        return None

    return TelegramProfile(
        telegram_user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
