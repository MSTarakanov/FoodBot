from __future__ import annotations

from office_food_bot.commands.approve import ApproveCommand
from office_food_bot.commands.balance import BalanceCommand
from office_food_bot.commands.catalog import CommandCatalog
from office_food_bot.commands.coffee import CoffeeCommand
from office_food_bot.commands.debug import DebugCommand
from office_food_bot.commands.eta import EtaCommand, MetaCommand
from office_food_bot.commands.help import HelpCommand
from office_food_bot.commands.hi import HiCommand
from office_food_bot.commands.lunch import (
    LunchAutoOffCommand,
    LunchAutoOnCommand,
    LunchAutoStatusCommand,
    LunchCommand,
)
from office_food_bot.commands.register import (
    CancelCommand,
    QuitCommand,
    RegisterCommand,
    RequestRegisterCommand,
)
from office_food_bot.commands.register_requests_list import RegisterRequestsListCommand
from office_food_bot.commands.start import StartCommand
from office_food_bot.commands.test_message import TestMessageCommand
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
            TestMessageCommand(),
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
