from __future__ import annotations

from dataclasses import dataclass

from office_food_bot.application.users.resolver import ActiveUserResolver
from office_food_bot.commanding.access import CommandAccessService
from office_food_bot.features.balance.use_case import GetBalanceReport
from office_food_bot.features.coffee.service import CoffeeService, CoffeeTimeResolver
from office_food_bot.features.debug.service import DebugService
from office_food_bot.features.invitations.service import InvitationPreferenceService
from office_food_bot.features.lunch.attendance import LunchAttendanceService
from office_food_bot.features.lunch.automation import (
    LunchAutoChatService,
    LunchPollPublisher,
    LunchSchedulerService,
)
from office_food_bot.features.lunch.calendar import BusinessCalendarService
from office_food_bot.features.lunch.pins import LunchPinService
from office_food_bot.features.polls.tracking import PollTrackingService
from office_food_bot.features.presence.service import PresenceService
from office_food_bot.features.registration.service import RegistrationService
from office_food_bot.features.vacation.service import VacationService
from office_food_bot.infrastructure.scheduler import JobScheduler
from office_food_bot.infrastructure.telegram_interactions import TelegramInteractionService
from office_food_bot.integrations.splitwise import SplitwiseService
from office_food_bot.messaging import BotMessenger


@dataclass(frozen=True)
class BotDependencies:
    messenger: BotMessenger
    telegram_bot_username: str
    timezone_name: str
    telegram_interactions: TelegramInteractionService
    registration: RegistrationService
    debug: DebugService
    command_access: CommandAccessService
    active_users: ActiveUserResolver
    invitations: InvitationPreferenceService
    coffee: CoffeeService
    coffee_time: CoffeeTimeResolver
    business_calendar: BusinessCalendarService
    presence: PresenceService
    get_balance_report: GetBalanceReport
    lunch_attendance: LunchAttendanceService
    vacation: VacationService
    lunch_auto_chats: LunchAutoChatService
    lunch_pins: LunchPinService
    lunch_publisher: LunchPollPublisher
    lunch_scheduler: LunchSchedulerService
    job_scheduler: JobScheduler
    poll_tracking: PollTrackingService
    splitwise: SplitwiseService
