from __future__ import annotations

from dataclasses import dataclass

from office_food_bot.services.balances import BalanceService
from office_food_bot.services.presence import PresenceService
from office_food_bot.services.registration import RegistrationService


@dataclass(frozen=True)
class BotServices:
    registration: RegistrationService
    presence: PresenceService
    balances: BalanceService
