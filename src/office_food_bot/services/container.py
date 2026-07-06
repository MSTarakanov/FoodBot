from __future__ import annotations

from dataclasses import dataclass

from office_food_bot.services.balances import BalanceService
from office_food_bot.services.command_access import CommandAccessService
from office_food_bot.services.debug import DebugService
from office_food_bot.services.lunch import LunchService
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
    presence: PresenceService
    balances: BalanceService
    lunch: LunchService
    poll_tracking: PollTrackingService
    splitwise: SplitwiseService
