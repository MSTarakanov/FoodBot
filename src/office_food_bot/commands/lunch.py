from __future__ import annotations

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commands.access import ensure_command_allowed
from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices
from office_food_bot.services.lunch import (
    LUNCH_PLACE_OTHER_OPTION_INDEX,
    LUNCH_PLACE_POLL_OPTIONS,
    LUNCH_PLACE_POLL_QUESTION,
    LUNCH_POLL_OPTIONS,
    LUNCH_POLL_QUESTION,
)
from office_food_bot.services.poll_tracking import PollAction


async def lunch_command(
    message: Message,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    if not await ensure_command_allowed(message, "lunch", messenger, services, state):
        return

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
    place_poll_message = await messenger.reply_poll(
        message,
        LUNCH_PLACE_POLL_QUESTION,
        LUNCH_PLACE_POLL_OPTIONS,
        is_anonymous=False,
        allows_multiple_answers=True,
        allow_adding_options=True,
    )
    if place_poll_message.poll is not None:
        services.poll_tracking.track_poll(
            place_poll_message.poll.id,
            message.chat.id,
            {LUNCH_PLACE_OTHER_OPTION_INDEX: PollAction.LUNCH_OTHER_FOOD_POLL},
        )
