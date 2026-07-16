from __future__ import annotations

from dataclasses import dataclass

from office_food_bot.commanding.catalog import CommandCatalog
from office_food_bot.commanding.validators import TelegramIdentityValidator
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
from office_food_bot.flows.catalog import FlowCatalog
from office_food_bot.flows.registration.factory import build_registration_flow
from office_food_bot.flows.registration.requests import (
    RegisterOtherAdminValidator,
    RegisterRequestParser,
)
from office_food_bot.flows.runner import FlowRunner
from office_food_bot.presenters.coffee import CoffeeCommandRenderer
from office_food_bot.previews import MESSAGE_PREVIEWS
from office_food_bot.services import BotServices


@dataclass(frozen=True, slots=True)
class CommandRuntime:
    catalog: CommandCatalog
    flow_runner: FlowRunner


def build_command_runtime(services: BotServices) -> CommandRuntime:
    messenger = services.messenger
    registration_flow = build_registration_flow(
        services.registration,
        services.invitations,
        services.splitwise,
    )
    flow_runner = FlowRunner(FlowCatalog((registration_flow,)), messenger)
    catalog: CommandCatalog | None = None

    def catalog_provider() -> CommandCatalog:
        if catalog is None:
            raise RuntimeError("Command catalog is not initialized")
        return catalog

    catalog = CommandCatalog(
        (
            StartCommand(messenger),
            HelpCommand(messenger, services.command_access, catalog_provider),
            HiCommand(
                messenger,
                services.telegram_interactions,
                services.telegram_bot_username,
            ),
            RegisterCommand(
                messenger,
                RegisterRequestParser(),
                (TelegramIdentityValidator(),),
                (RegisterOtherAdminValidator(services.registration),),
                flow_runner,
                registration_flow,
            ),
            RequestRegisterCommand(messenger, services.registration),
            QuitCommand(messenger, services.registration),
            CancelCommand(messenger, flow_runner),
            ApproveCommand(messenger, services.registration),
            RegisterRequestsListCommand(messenger, services.registration),
            DebugCommand(
                messenger,
                services.debug,
                services.command_access,
                catalog_provider,
            ),
            TestCommand(messenger, MESSAGE_PREVIEWS),
            MetaCommand(messenger, services.presence, services.active_users),
            EtaCommand(messenger, services.presence, services.active_users),
            BalanceCommand(messenger, services.balances, services.active_users),
            VacationCommand(messenger, services.vacation, services.active_users),
            LunchCommand(
                messenger,
                services.command_access,
                services.invitations,
                services.active_users,
                services.lunch_publisher,
            ),
            CoffeeCommand(
                messenger,
                services.coffee,
                services.coffee_time,
                CoffeeCommandRenderer(services.timezone_name),
                services.invitations,
                services.command_access,
            ),
            LunchAutoOnCommand(messenger, services.lunch_auto_chats),
            LunchAutoOffCommand(messenger, services.lunch_auto_chats),
            LunchAutoStatusCommand(messenger, services.lunch_auto_chats),
        )
    )
    return CommandRuntime(catalog, flow_runner)
