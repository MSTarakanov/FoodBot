from __future__ import annotations

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices
from office_food_bot.services.lunch import LUNCH_POLL_OPTIONS, LUNCH_POLL_QUESTION


async def lunch_command(
    message: Message,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    await state.clear()
    profile = telegram_profile_from_message(message)
    if profile is None:
        await messenger.reply(message, "Не вижу твой Telegram user id.")
        return

    block_reason = services.lunch.poll_block_reason(profile.telegram_user_id)
    if block_reason is not None:
        await messenger.reply(message, block_reason)
        return

    await messenger.reply_poll(
        message,
        LUNCH_POLL_QUESTION,
        LUNCH_POLL_OPTIONS,
        is_anonymous=False,
        allows_multiple_answers=False,
        allow_adding_options=True,
    )
