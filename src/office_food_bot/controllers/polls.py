from __future__ import annotations

from typing import assert_never

from aiogram import Bot
from aiogram.types import PollAnswer

from office_food_bot.services.lunch_auto import LunchPollPublisher
from office_food_bot.services.lunch_polls import LUNCH_OTHER_FOOD_POLL
from office_food_bot.services.poll_tracking import PollAction, PollTrackingService


class PollAnswerController:
    def __init__(
        self,
        poll_tracking: PollTrackingService,
        lunch_publisher: LunchPollPublisher,
    ) -> None:
        self._poll_tracking = poll_tracking
        self._lunch_publisher = lunch_publisher

    async def handle(self, poll_answer: PollAnswer, bot: Bot) -> None:
        if poll_answer.user is None:
            return
        action_requests = self._poll_tracking.consume_action_requests(
            poll_answer.poll_id,
            poll_answer.user.id,
            tuple(poll_answer.option_ids),
        )
        for action_request in action_requests:
            match action_request.action:
                case PollAction.LUNCH_OTHER_FOOD_POLL:
                    await self._lunch_publisher.send_poll(
                        bot,
                        action_request.chat_id,
                        LUNCH_OTHER_FOOD_POLL,
                        action_request.context_date,
                    )
                case _:
                    assert_never(action_request.action)
