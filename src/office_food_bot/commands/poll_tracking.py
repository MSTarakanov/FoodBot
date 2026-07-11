from __future__ import annotations

from aiogram import Bot
from aiogram.types import PollAnswer

from office_food_bot.services import BotServices
from office_food_bot.services.lunch_polls import LUNCH_OTHER_FOOD_POLL
from office_food_bot.services.poll_tracking import PollAction


async def poll_answer_handler(
    poll_answer: PollAnswer,
    bot: Bot,
    services: BotServices,
) -> None:
    if poll_answer.user is None:
        return
    action_requests = services.poll_tracking.consume_action_requests(
        poll_answer.poll_id,
        poll_answer.user.id,
        tuple(poll_answer.option_ids),
    )
    for action_request in action_requests:
        if action_request.action == PollAction.LUNCH_OTHER_FOOD_POLL:
            await services.lunch_publisher.send_poll(
                bot,
                action_request.chat_id,
                LUNCH_OTHER_FOOD_POLL,
                action_request.context_date,
            )
