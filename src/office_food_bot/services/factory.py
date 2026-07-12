from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from office_food_bot.coffee_repositories import CoffeeSessionRepository
from office_food_bot.database import Database
from office_food_bot.invitation_repositories import InvitationPreferenceRepository
from office_food_bot.messaging import BotMessenger
from office_food_bot.repositories import (
    DebugRepository,
    LunchAutoChatRepository,
    LunchPinRepository,
    PollRepository,
    RegistrationRequestRepository,
    TelegramAccountRepository,
    UserRepository,
    VacationRepository,
)
from office_food_bot.services.balances import BalanceService
from office_food_bot.services.business_calendar import BusinessCalendarService
from office_food_bot.services.coffee import CoffeeService
from office_food_bot.services.command_access import CommandAccessService
from office_food_bot.services.container import BotServices
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
from office_food_bot.services.lunch_polls import (
    LUNCH_POLL_DEFINITION_CATALOG,
    LunchPollCatalog,
)
from office_food_bot.services.poll_tracking import PollTrackingService
from office_food_bot.services.presence import PresenceService
from office_food_bot.services.registration import RegistrationService
from office_food_bot.services.splitwise import (
    HttpSplitwiseClient,
    SplitwiseGroupClient,
    SplitwiseService,
)
from office_food_bot.services.telegram_interactions import TelegramInteractionService
from office_food_bot.services.vacation import VacationService


def build_services(
    database: Database,
    telegram_bot_username: str,
    admin_ids: frozenset[int],
    timezone_name: str,
    splitwise_api_key: str | None,
    splitwise_group_id: int | None,
    clock: Callable[[], datetime] | None = None,
    splitwise_client: SplitwiseGroupClient | None = None,
) -> BotServices:
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
    invitations = InvitationPreferenceService(users, invitation_preferences)
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
    coffee = CoffeeService(
        users,
        invitations,
        coffee_sessions,
        lunch_attendance,
        messenger,
        job_scheduler,
        timezone_name,
        clock,
    )
    return BotServices(
        telegram_bot_username=telegram_bot_username,
        telegram_interactions=TelegramInteractionService(telegram_accounts),
        registration=registration,
        debug=debug,
        command_access=CommandAccessService(registration, debug),
        invitations=invitations,
        coffee=coffee,
        business_calendar=business_calendar,
        presence=PresenceService(users, timezone_name, clock),
        balances=BalanceService(users, splitwise),
        lunch=LunchService(users),
        lunch_attendance=lunch_attendance,
        vacation=VacationService(users, vacations, timezone_name, clock),
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
