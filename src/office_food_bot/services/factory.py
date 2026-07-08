from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from office_food_bot.database import Database
from office_food_bot.messaging import BotMessenger
from office_food_bot.repositories import (
    DebugRepository,
    LunchAutoChatRepository,
    RegistrationRequestRepository,
    TelegramAccountRepository,
    UserRepository,
    VacationRepository,
)
from office_food_bot.services.balances import BalanceService
from office_food_bot.services.business_calendar import BusinessCalendarService
from office_food_bot.services.command_access import CommandAccessService
from office_food_bot.services.container import BotServices
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
    vacations = VacationRepository(database)
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
    debug = DebugService(debug_settings)
    business_calendar = BusinessCalendarService()
    poll_tracking = PollTrackingService()
    lunch_auto_chats = LunchAutoChatService(lunch_auto_chat_repository)
    lunch_publisher = LunchPollPublisher(
        BotMessenger(),
        poll_tracking,
        users,
        vacations,
        timezone_name,
        clock,
    )
    return BotServices(
        telegram_bot_username=telegram_bot_username,
        telegram_interactions=TelegramInteractionService(telegram_accounts),
        registration=registration,
        debug=debug,
        command_access=CommandAccessService(registration, debug),
        business_calendar=business_calendar,
        presence=PresenceService(users, timezone_name, clock),
        balances=BalanceService(users, splitwise),
        lunch=LunchService(users),
        vacation=VacationService(users, vacations, timezone_name, clock),
        lunch_auto_chats=lunch_auto_chats,
        lunch_publisher=lunch_publisher,
        lunch_scheduler=LunchSchedulerService(
            lunch_auto_chats,
            business_calendar,
            lunch_publisher,
            timezone_name,
            clock,
        ),
        poll_tracking=poll_tracking,
        splitwise=splitwise,
    )
