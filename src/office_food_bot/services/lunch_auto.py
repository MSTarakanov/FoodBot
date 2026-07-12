from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from enum import StrEnum
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from office_food_bot.execution import CommandExecutionMode
from office_food_bot.messaging import BotMessenger
from office_food_bot.models import LunchAutoChat, RegisteredUser
from office_food_bot.repositories import (
    LunchAutoChatRepository,
    UserRepository,
    VacationRepository,
)
from office_food_bot.services.business_calendar import BusinessCalendarService
from office_food_bot.services.job_scheduler import JobScheduler
from office_food_bot.services.lunch import lunch_announcement_text
from office_food_bot.services.lunch_pin import LunchPinService
from office_food_bot.services.lunch_polls import LunchOfficeSelection, LunchPollCatalog
from office_food_bot.services.poll_tracking import PollTrackingService
from office_food_bot.services.polls import PollDefinition

AUTO_LUNCH_JOB_ID = "auto_lunch"


class LunchPublishKind(StrEnum):
    PUBLISHED = "published"
    SKIPPED_ALL_ON_VACATION = "skipped_all_on_vacation"


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
        users: UserRepository,
        vacations: VacationRepository,
        lunch_pins: LunchPinService,
        poll_catalog: LunchPollCatalog,
        timezone_name: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._messenger = messenger
        self._poll_tracking = poll_tracking
        self._users = users
        self._vacations = vacations
        self._lunch_pins = lunch_pins
        self._poll_catalog = poll_catalog
        self._timezone = ZoneInfo(timezone_name)
        self._clock = clock or (lambda: datetime.now(tz=UTC))

    async def publish(
        self,
        bot: Bot,
        chat_id: int,
        *,
        mode: CommandExecutionMode,
        office_selection: LunchOfficeSelection,
    ) -> LunchPublishKind:
        today = self._clock().astimezone(self._timezone).date()
        polls = self._poll_catalog.select(office_selection, today)
        active_users = self._active_users_available_for_lunch()
        if not active_users and mode == CommandExecutionMode.AUTOMATIC:
            return LunchPublishKind.SKIPPED_ALL_ON_VACATION

        await self._messenger.send(
            bot,
            chat_id,
            lunch_announcement_text(active_users),
        )
        lunch_poll_message = await self.send_poll(
            bot,
            chat_id,
            polls.lunch,
            today,
        )
        if mode == CommandExecutionMode.AUTOMATIC:
            await self._lunch_pins.replace_pin(
                bot,
                chat_id,
                lunch_poll_message.message_id,
                today,
            )

        await self.send_poll(
            bot,
            chat_id,
            polls.place,
            today,
        )
        return LunchPublishKind.PUBLISHED

    async def send_poll(
        self,
        bot: Bot,
        chat_id: int,
        definition: PollDefinition,
        context_date: date,
    ) -> Message:
        message = await self._messenger.send_poll(
            bot,
            chat_id,
            definition.question,
            definition.options,
            is_anonymous=False,
            allows_multiple_answers=definition.allows_multiple_answers,
            allow_adding_options=True,
        )
        if message.poll is not None:
            self._poll_tracking.register_poll(
                message.poll.id,
                chat_id,
                message.message_id,
                definition,
                context_date,
            )
        return message

    def _active_users_available_for_lunch(self) -> tuple[RegisteredUser, ...]:
        today = self._clock().astimezone(self._timezone).date()
        vacation_user_ids = self._vacations.active_user_ids(today)
        return tuple(
            user
            for user in self._users.list_active_users()
            if user.id not in vacation_user_ids
        )


class LunchSchedulerService:
    def __init__(
        self,
        auto_chats: LunchAutoChatService,
        calendar: BusinessCalendarService,
        publisher: LunchPollPublisher,
        lunch_pins: LunchPinService,
        scheduler: JobScheduler,
        timezone_name: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._auto_chats = auto_chats
        self._calendar = calendar
        self._publisher = publisher
        self._lunch_pins = lunch_pins
        self._scheduler = scheduler
        self._timezone = ZoneInfo(timezone_name)
        self._clock = clock or (lambda: datetime.now(tz=UTC))

    def register_job(self, bot: Bot) -> None:
        async def run() -> None:
            await self.run_due_lunch(bot)

        self._scheduler.add_weekday_cron(
            AUTO_LUNCH_JOB_ID,
            run,
            hour=11,
            minute=30,
        )

    async def run_due_lunch(self, bot: Bot) -> None:
        today = self._clock().astimezone(self._timezone).date()
        enabled_chats = self._auto_chats.list_enabled()
        await self._clear_saved_lunch_pins(bot, enabled_chats)
        if not self._calendar.is_working_day(today):
            return

        for chat in enabled_chats:
            try:
                await self._publisher.publish(
                    bot,
                    chat.chat_id,
                    mode=CommandExecutionMode.AUTOMATIC,
                    office_selection=LunchOfficeSelection.AUTOMATIC,
                )
            except TelegramAPIError:
                continue

    async def _clear_saved_lunch_pins(
        self,
        bot: Bot,
        chats: tuple[LunchAutoChat, ...],
    ) -> None:
        for chat in chats:
            await self._lunch_pins.clear_saved_pin(bot, chat.chat_id)
