from __future__ import annotations

from dataclasses import dataclass

from office_food_bot.services.balances import BalanceService
from office_food_bot.services.business_calendar import BusinessCalendarService
from office_food_bot.services.coffee import CoffeeService
from office_food_bot.services.command_access import CommandAccessService
from office_food_bot.services.debug import DebugService
from office_food_bot.services.invitations import InvitationPreferenceService
from office_food_bot.services.job_scheduler import JobScheduler
from office_food_bot.services.lunch import LunchService
from office_food_bot.services.lunch_attendance import LunchAttendanceService
from office_food_bot.services.lunch_auto import (
    LunchAutoChatService,
    LunchPollPublisher,
    LunchSchedulerService,
)
from office_food_bot.services.lunch_pin import LunchPinService
from office_food_bot.services.poll_tracking import PollTrackingService
from office_food_bot.services.presence import PresenceService
from office_food_bot.services.registration import RegistrationService
from office_food_bot.services.splitwise import SplitwiseService
from office_food_bot.services.telegram_interactions import TelegramInteractionService
from office_food_bot.services.vacation import VacationService


@dataclass(frozen=True)
class BotServices:
    telegram_bot_username: str
    telegram_interactions: TelegramInteractionService
    registration: RegistrationService
    debug: DebugService
    command_access: CommandAccessService
    invitations: InvitationPreferenceService
    coffee: CoffeeService
    business_calendar: BusinessCalendarService
    presence: PresenceService
    balances: BalanceService
    lunch: LunchService
    lunch_attendance: LunchAttendanceService
    vacation: VacationService
    lunch_auto_chats: LunchAutoChatService
    lunch_pins: LunchPinService
    lunch_publisher: LunchPollPublisher
    lunch_scheduler: LunchSchedulerService
    job_scheduler: JobScheduler
    poll_tracking: PollTrackingService
    splitwise: SplitwiseService
