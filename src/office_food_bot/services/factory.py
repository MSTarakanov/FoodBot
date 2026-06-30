from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from office_food_bot.database import Database
from office_food_bot.repositories import UserRepository
from office_food_bot.services.balances import BalanceService
from office_food_bot.services.container import BotServices
from office_food_bot.services.presence import PresenceService
from office_food_bot.services.registration import RegistrationService


def build_services(
    database: Database,
    admin_ids: frozenset[int],
    timezone_name: str,
    clock: Callable[[], datetime] | None = None,
) -> BotServices:
    users = UserRepository(database)
    return BotServices(
        registration=RegistrationService(users, admin_ids),
        presence=PresenceService(users, timezone_name, clock),
        balances=BalanceService(users),
    )
