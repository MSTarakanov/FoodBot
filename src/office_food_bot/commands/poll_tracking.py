from __future__ import annotations

from aiogram import Bot
from aiogram.types import PollAnswer

from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices
from office_food_bot.services.lunch import (
    LUNCH_OTHER_FOOD_POLL_OPTIONS,
    LUNCH_OTHER_FOOD_POLL_QUESTION,
)
from office_food_bot.services.poll_tracking import PollAction


async def poll_answer_handler(
    poll_answer: PollAnswer,
    bot: Bot,
    messenger: BotMessenger,
    services: BotServices,
) -> None:
    action_requests = services.poll_tracking.consume_action_requests(
        poll_answer.poll_id,
        tuple(poll_answer.option_ids),
    )
    for action_request in action_requests:
        if action_request.action == PollAction.LUNCH_OTHER_FOOD_POLL:
            await messenger.send_poll(
                bot,
                action_request.chat_id,
                LUNCH_OTHER_FOOD_POLL_QUESTION,
                LUNCH_OTHER_FOOD_POLL_OPTIONS,
                is_anonymous=False,
                allows_multiple_answers=True,
                allow_adding_options=True,
            )
