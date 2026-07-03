from __future__ import annotations

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.commands.definitions import help_text
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices


async def help_command(
    message: Message,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    await state.clear()
    profile = telegram_profile_from_message(message)
    is_admin = (
        profile is not None
        and services.registration.can_approve(profile.telegram_user_id)
    )
    await messenger.reply(message, help_text(is_admin=is_admin))
