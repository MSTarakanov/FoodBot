from __future__ import annotations

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices

COMMAND_UNAVAILABLE_TEXT = "Команда недоступна."


async def ensure_command_allowed(
    message: Message,
    command_name: str,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> bool:
    profile = telegram_profile_from_message(message)
    telegram_user_id = None
    if profile is not None:
        telegram_user_id = profile.telegram_user_id

    access = services.command_access.can_run(
        command_name,
        str(message.chat.type),
        telegram_user_id,
    )
    if access.allowed:
        return True

    await state.clear()
    await messenger.reply(message, access.message or COMMAND_UNAVAILABLE_TEXT)
    return False
