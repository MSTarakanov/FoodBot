from __future__ import annotations

from dataclasses import dataclass

from office_food_bot.services.balances import BalanceService
from office_food_bot.services.business_calendar import BusinessCalendarService
from office_food_bot.services.command_access import CommandAccessService
from office_food_bot.services.debug import DebugService
from office_food_bot.services.lunch import LunchService
from office_food_bot.services.lunch_auto import (
    LunchAutoChatService,
    LunchPollPublisher,
    LunchSchedulerService,
)
from office_food_bot.services.poll_tracking import PollTrackingService
from office_food_bot.services.presence import PresenceService
from office_food_bot.services.registration import RegistrationService
from office_food_bot.services.splitwise import SplitwiseService


@dataclass(frozen=True)
class BotServices:
    telegram_bot_username: str
    registration: RegistrationService
    debug: DebugService
    command_access: CommandAccessService
    business_calendar: BusinessCalendarService
    presence: PresenceService
    balances: BalanceService
    lunch: LunchService
    lunch_auto_chats: LunchAutoChatService
    lunch_publisher: LunchPollPublisher
    lunch_scheduler: LunchSchedulerService
    poll_tracking: PollTrackingService
    splitwise: SplitwiseService
