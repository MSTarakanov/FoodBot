from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from office_food_bot.application.users.resolver import ActiveUserResolver
from office_food_bot.bootstrap.dependencies import BotDependencies
from office_food_bot.commanding.access import CommandAccessService
from office_food_bot.database import Database
from office_food_bot.features.balance.repository import BalanceRepository
from office_food_bot.features.balance.use_case import GetBalanceReport
from office_food_bot.features.coffee.jobs import CoffeeJobCoordinator
from office_food_bot.features.coffee.locks import CoffeeChatLocks
from office_food_bot.features.coffee.publisher import CoffeeCardPublisher
from office_food_bot.features.coffee.rendering import CoffeeCardRenderer
from office_food_bot.features.coffee.repository import CoffeeSessionRepository
from office_food_bot.features.coffee.session import CoffeeSessionService
from office_food_bot.features.coffee.time import CoffeeTimeResolver
from office_food_bot.features.debug.repository import DebugRepository
from office_food_bot.features.debug.service import DebugService
from office_food_bot.features.invitations.repository import InvitationPreferenceRepository
from office_food_bot.features.invitations.service import InvitationPreferenceService
from office_food_bot.features.lunch.attendance import LunchAttendanceService
from office_food_bot.features.lunch.automation import (
    LunchAutoChatService,
    LunchPollPublisher,
    LunchSchedulerService,
)
from office_food_bot.features.lunch.calendar import BusinessCalendarService
from office_food_bot.features.lunch.pins import LunchPinService
from office_food_bot.features.lunch.polls import (
    LUNCH_POLL_DEFINITION_CATALOG,
    LunchPollCatalog,
)
from office_food_bot.features.lunch.repository import (
    LunchAutoChatRepository,
    LunchPinRepository,
)
from office_food_bot.features.polls.repository import PollRepository
from office_food_bot.features.polls.tracking import PollTrackingService
from office_food_bot.features.presence.service import PresenceService
from office_food_bot.features.registration.repository import (
    RegistrationRequestRepository,
    TelegramAccountRepository,
)
from office_food_bot.features.registration.service import RegistrationService
from office_food_bot.features.vacation.repository import VacationRepository
from office_food_bot.features.vacation.service import VacationService
from office_food_bot.infrastructure.persistence.users import UserRepository
from office_food_bot.infrastructure.scheduler import JobScheduler
from office_food_bot.infrastructure.telegram_interactions import TelegramInteractionService
from office_food_bot.integrations.splitwise import (
    HttpSplitwiseClient,
    SplitwiseGroupClient,
    SplitwiseService,
)
from office_food_bot.messaging import BotMessenger


def build_dependencies(
    database: Database,
    telegram_bot_username: str,
    admin_ids: frozenset[int],
    timezone_name: str,
    splitwise_api_key: str | None,
    splitwise_group_id: int | None,
    clock: Callable[[], datetime] | None = None,
    splitwise_client: SplitwiseGroupClient | None = None,
) -> BotDependencies:
    users = UserRepository(database)
    telegram_accounts = TelegramAccountRepository(database)
    registration_requests = RegistrationRequestRepository(database)
    debug_settings = DebugRepository(database)
    lunch_auto_chat_repository = LunchAutoChatRepository(database)
    lunch_pin_repository = LunchPinRepository(database)
    poll_repository = PollRepository(database)
    vacations = VacationRepository(database)
    invitation_preferences = InvitationPreferenceRepository(database)
    coffee_sessions = CoffeeSessionRepository(database)
    balance_repository = BalanceRepository(database)
    client = splitwise_client
    if client is None and splitwise_api_key is not None:
        client = HttpSplitwiseClient(splitwise_api_key)

    splitwise = SplitwiseService(client, splitwise_group_id)
    registration = RegistrationService(
        users,
        telegram_accounts,
        registration_requests,
        admin_ids,
    )
    active_users = ActiveUserResolver(users)
    invitations = InvitationPreferenceService(active_users, invitation_preferences)
    debug = DebugService(debug_settings)
    business_calendar = BusinessCalendarService()
    poll_tracking = PollTrackingService(
        poll_repository,
        LUNCH_POLL_DEFINITION_CATALOG,
        clock,
    )
    messenger = BotMessenger()
    lunch_pins = LunchPinService(messenger, lunch_pin_repository)
    lunch_auto_chats = LunchAutoChatService(lunch_auto_chat_repository)
    lunch_publisher = LunchPollPublisher(
        messenger,
        poll_tracking,
        users,
        vacations,
        invitations,
        lunch_pins,
        LunchPollCatalog(),
        timezone_name,
        clock,
    )
    job_scheduler = JobScheduler(timezone_name)
    lunch_attendance = LunchAttendanceService(poll_repository)
    coffee_time = CoffeeTimeResolver(timezone_name, clock)
    coffee_locks = CoffeeChatLocks()
    coffee_publisher = CoffeeCardPublisher(
        users,
        invitations,
        lunch_attendance,
        messenger,
        CoffeeCardRenderer(timezone_name),
        timezone_name,
        clock,
    )
    coffee_jobs = CoffeeJobCoordinator(
        coffee_sessions,
        coffee_publisher,
        job_scheduler,
        coffee_locks,
        clock,
    )
    coffee = CoffeeSessionService(
        invitations,
        coffee_sessions,
        coffee_publisher,
        coffee_jobs,
        coffee_locks,
        clock,
    )
    return BotDependencies(
        messenger=messenger,
        telegram_bot_username=telegram_bot_username,
        timezone_name=timezone_name,
        telegram_interactions=TelegramInteractionService(telegram_accounts),
        registration=registration,
        debug=debug,
        command_access=CommandAccessService(registration, debug),
        active_users=active_users,
        invitations=invitations,
        coffee=coffee,
        coffee_jobs=coffee_jobs,
        coffee_time=coffee_time,
        business_calendar=business_calendar,
        presence=PresenceService(active_users, timezone_name, clock),
        get_balance_report=GetBalanceReport(balance_repository, splitwise),
        lunch_attendance=lunch_attendance,
        vacation=VacationService(active_users, vacations, timezone_name, clock),
        lunch_auto_chats=lunch_auto_chats,
        lunch_pins=lunch_pins,
        lunch_publisher=lunch_publisher,
        lunch_scheduler=LunchSchedulerService(
            lunch_auto_chats,
            business_calendar,
            lunch_publisher,
            lunch_pins,
            job_scheduler,
            timezone_name,
            clock,
        ),
        job_scheduler=job_scheduler,
        poll_tracking=poll_tracking,
        splitwise=splitwise,
    )
