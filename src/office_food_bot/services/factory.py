from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from office_food_bot.database import Database
from office_food_bot.repositories import DebugRepository, UserRepository
from office_food_bot.services.balances import BalanceService
from office_food_bot.services.command_access import CommandAccessService
from office_food_bot.services.container import BotServices
from office_food_bot.services.debug import DebugService
from office_food_bot.services.lunch import LunchService
from office_food_bot.services.poll_tracking import PollTrackingService
from office_food_bot.services.presence import PresenceService
from office_food_bot.services.registration import RegistrationService
from office_food_bot.services.splitwise import (
    HttpSplitwiseClient,
    SplitwiseGroupClient,
    SplitwiseService,
)


def build_services(
    database: Database,
    admin_ids: frozenset[int],
    timezone_name: str,
    splitwise_api_key: str | None,
    splitwise_group_id: int | None,
    clock: Callable[[], datetime] | None = None,
    splitwise_client: SplitwiseGroupClient | None = None,
) -> BotServices:
    users = UserRepository(database)
    debug_settings = DebugRepository(database)
    client = splitwise_client
    if client is None and splitwise_api_key is not None:
        client = HttpSplitwiseClient(splitwise_api_key)

    splitwise = SplitwiseService(client, splitwise_group_id)
    registration = RegistrationService(users, admin_ids)
    debug = DebugService(debug_settings)
    return BotServices(
        registration=registration,
        debug=debug,
        command_access=CommandAccessService(registration, debug),
        presence=PresenceService(users, timezone_name, clock),
        balances=BalanceService(users, splitwise),
        lunch=LunchService(users),
        poll_tracking=PollTrackingService(),
        splitwise=splitwise,
    )
