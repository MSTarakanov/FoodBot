from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]

from office_food_bot.messaging import BotMessenger
from office_food_bot.models import LunchAutoChat
from office_food_bot.repositories import LunchAutoChatRepository
from office_food_bot.services.business_calendar import BusinessCalendarService
from office_food_bot.services.lunch import (
    LUNCH_PLACE_OTHER_OPTION_INDEX,
    LUNCH_PLACE_POLL_OPTIONS,
    LUNCH_PLACE_POLL_QUESTION,
    LUNCH_POLL_OPTIONS,
    LUNCH_POLL_QUESTION,
)
from office_food_bot.services.poll_tracking import PollAction, PollTrackingService

AUTO_LUNCH_JOB_ID = "auto_lunch"


class LunchAutoChatService:
    def __init__(self, chats: LunchAutoChatRepository) -> None:
        self._chats = chats

    def enable(self, chat_id: int, title: str | None) -> LunchAutoChat:
        return self._chats.enable(chat_id, title)

    def disable(self, chat_id: int) -> LunchAutoChat | None:
        return self._chats.disable(chat_id)

    def status_text(self, chat_id: int) -> str:
        chat = self._chats.get(chat_id)
        if chat is not None and chat.enabled:
            return "Авто-ланч включен для этого чата."
        return "Авто-ланч выключен для этого чата."

    def list_enabled(self) -> tuple[LunchAutoChat, ...]:
        return self._chats.list_enabled()


class LunchPollPublisher:
    def __init__(
        self,
        messenger: BotMessenger,
        poll_tracking: PollTrackingService,
    ) -> None:
        self._messenger = messenger
        self._poll_tracking = poll_tracking

    async def publish(self, bot: Bot, chat_id: int) -> None:
        await self._messenger.send_poll(
            bot,
            chat_id,
            LUNCH_POLL_QUESTION,
            LUNCH_POLL_OPTIONS,
            is_anonymous=False,
            allows_multiple_answers=False,
            allow_adding_options=True,
        )
        place_poll_message = await self._messenger.send_poll(
            bot,
            chat_id,
            LUNCH_PLACE_POLL_QUESTION,
            LUNCH_PLACE_POLL_OPTIONS,
            is_anonymous=False,
            allows_multiple_answers=True,
            allow_adding_options=True,
        )
        if place_poll_message.poll is not None:
            self._poll_tracking.track_poll(
                place_poll_message.poll.id,
                chat_id,
                {LUNCH_PLACE_OTHER_OPTION_INDEX: PollAction.LUNCH_OTHER_FOOD_POLL},
            )


class LunchSchedulerService:
    def __init__(
        self,
        auto_chats: LunchAutoChatService,
        calendar: BusinessCalendarService,
        publisher: LunchPollPublisher,
        timezone_name: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._auto_chats = auto_chats
        self._calendar = calendar
        self._publisher = publisher
        self._timezone = ZoneInfo(timezone_name)
        self._clock = clock or (lambda: datetime.now(tz=UTC))
        self._scheduler: AsyncIOScheduler | None = None  # type: ignore[no-any-unimported]

    def start(self, bot: Bot) -> None:
        if self._scheduler is not None:
            return

        scheduler = AsyncIOScheduler(timezone=self._timezone)
        scheduler.add_job(
            self.run_due_lunch,
            trigger=CronTrigger(
                day_of_week="mon-fri",
                hour=11,
                minute=30,
                timezone=self._timezone,
            ),
            args=(bot,),
            id=AUTO_LUNCH_JOB_ID,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        scheduler.start()
        self._scheduler = scheduler

    def shutdown(self) -> None:
        if self._scheduler is None:
            return

        self._scheduler.shutdown(wait=False)
        self._scheduler = None

    async def run_due_lunch(self, bot: Bot) -> None:
        today = self._clock().astimezone(self._timezone).date()
        if not self._calendar.is_working_day(today):
            return

        for chat in self._auto_chats.list_enabled():
            try:
                await self._publisher.publish(bot, chat.chat_id)
            except TelegramAPIError:
                continue
