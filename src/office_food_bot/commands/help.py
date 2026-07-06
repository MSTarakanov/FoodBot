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
    telegram_user_id = None
    if profile is not None:
        telegram_user_id = profile.telegram_user_id

    await messenger.reply(
        message,
        help_text(
            services.command_access.visible_commands(
                str(message.chat.type),
                telegram_user_id,
            )
        ),
    )
