from __future__ import annotations

from office_food_bot.commanding.catalog import CommandCatalog
from office_food_bot.commands.approve import ApproveCommand
from office_food_bot.commands.balance import BalanceCommand
from office_food_bot.commands.cancel import CancelCommand
from office_food_bot.commands.coffee import CoffeeCommand
from office_food_bot.commands.debug import DebugCommand
from office_food_bot.commands.eta import EtaCommand
from office_food_bot.commands.help import HelpCommand
from office_food_bot.commands.hi import HiCommand
from office_food_bot.commands.lunch import LunchCommand
from office_food_bot.commands.lunch_auto_off import LunchAutoOffCommand
from office_food_bot.commands.lunch_auto_on import LunchAutoOnCommand
from office_food_bot.commands.lunch_auto_status import LunchAutoStatusCommand
from office_food_bot.commands.meta import MetaCommand
from office_food_bot.commands.quit import QuitCommand
from office_food_bot.commands.register import RegisterCommand
from office_food_bot.commands.register_requests_list import RegisterRequestsListCommand
from office_food_bot.commands.request_register import RequestRegisterCommand
from office_food_bot.commands.start import StartCommand
from office_food_bot.commands.test import TestCommand
from office_food_bot.commands.vacation import VacationCommand
from office_food_bot.services import BotServices


def build_command_catalog(services: BotServices) -> CommandCatalog:
    return CommandCatalog(
        (
            StartCommand(),
            HelpCommand(services),
            HiCommand(services),
            RegisterCommand(services),
            RequestRegisterCommand(services),
            QuitCommand(services),
            CancelCommand(),
            ApproveCommand(services),
            RegisterRequestsListCommand(services),
            DebugCommand(services),
            TestCommand(),
            MetaCommand(services),
            EtaCommand(services),
            BalanceCommand(services.balances, services.active_users),
            VacationCommand(services),
            LunchCommand(services),
            CoffeeCommand(services),
            LunchAutoOnCommand(services),
            LunchAutoOffCommand(services),
            LunchAutoStatusCommand(services),
        )
    )
