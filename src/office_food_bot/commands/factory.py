from __future__ import annotations

from dataclasses import dataclass

from office_food_bot.bootstrap import BotDependencies
from office_food_bot.commanding.catalog import CommandCatalog
from office_food_bot.commanding.errors.models import CommonErrorCode
from office_food_bot.commanding.errors.rendering import ErrorRenderer
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
from office_food_bot.features.balance.errors import BalanceErrorRenderer
from office_food_bot.features.coffee.rendering import CoffeeCommandRenderer
from office_food_bot.features.registration.errors import RegistrationErrorRenderer
from office_food_bot.features.registration.flow.factory import build_registration_flow
from office_food_bot.features.registration.flow.requests import (
    RegisterOtherAdminValidator,
    RegisterRequestParser,
    RegisterRequestResolver,
)
from office_food_bot.flows.catalog import FlowCatalog
from office_food_bot.flows.runner import FlowRunner
from office_food_bot.previews.registry import MESSAGE_PREVIEWS


@dataclass(frozen=True, slots=True)
class CommandRuntime:
    catalog: CommandCatalog
    flow_runner: FlowRunner


def build_command_runtime(
    dependencies: BotDependencies,
    common_error_renderer: ErrorRenderer[CommonErrorCode],
) -> CommandRuntime:
    messenger = dependencies.messenger
    registration_flow = build_registration_flow(
        dependencies.registration,
        dependencies.invitations,
        dependencies.splitwise,
    )
    flow_runner = FlowRunner(FlowCatalog((registration_flow,)), messenger)
    catalog: CommandCatalog | None = None

    def catalog_provider() -> CommandCatalog:
        if catalog is None:
            raise RuntimeError("Command catalog is not initialized")
        return catalog

    catalog = CommandCatalog(
        (
            StartCommand(messenger, common_error_renderer),
            HelpCommand(
                messenger,
                common_error_renderer,
                dependencies.command_access,
                catalog_provider,
            ),
            HiCommand(
                messenger,
                common_error_renderer,
                dependencies.telegram_interactions,
                dependencies.telegram_bot_username,
            ),
            RegisterCommand(
                messenger,
                common_error_renderer,
                RegisterRequestParser(),
                (TelegramIdentityValidator(),),
                (RegisterOtherAdminValidator(dependencies.registration),),
                RegisterRequestResolver(),
                flow_runner,
                registration_flow,
            ),
            RequestRegisterCommand(
                messenger,
                common_error_renderer,
                dependencies.registration,
                RegistrationErrorRenderer(),
            ),
            QuitCommand(messenger, common_error_renderer, dependencies.registration),
            CancelCommand(messenger, common_error_renderer, flow_runner),
            ApproveCommand(messenger, common_error_renderer, dependencies.registration),
            RegisterRequestsListCommand(
                messenger,
                common_error_renderer,
                dependencies.registration,
            ),
            DebugCommand(
                messenger,
                common_error_renderer,
                dependencies.debug,
                dependencies.command_access,
                catalog_provider,
            ),
            TestCommand(messenger, common_error_renderer, MESSAGE_PREVIEWS),
            MetaCommand(
                messenger,
                common_error_renderer,
                dependencies.presence,
                dependencies.active_users,
            ),
            EtaCommand(
                messenger,
                common_error_renderer,
                dependencies.presence,
                dependencies.active_users,
            ),
            BalanceCommand(
                messenger,
                common_error_renderer,
                dependencies.get_balance_report,
                dependencies.active_users,
                BalanceErrorRenderer(),
            ),
            VacationCommand(
                messenger,
                common_error_renderer,
                dependencies.vacation,
                dependencies.active_users,
            ),
            LunchCommand(
                messenger,
                common_error_renderer,
                dependencies.command_access,
                dependencies.invitations,
                dependencies.active_users,
                dependencies.lunch_publisher,
            ),
            CoffeeCommand(
                messenger,
                common_error_renderer,
                dependencies.coffee,
                dependencies.coffee_time,
                CoffeeCommandRenderer(dependencies.timezone_name),
                dependencies.invitations,
                dependencies.command_access,
                dependencies.active_users,
            ),
            LunchAutoOnCommand(
                messenger,
                common_error_renderer,
                dependencies.lunch_auto_chats,
            ),
            LunchAutoOffCommand(
                messenger,
                common_error_renderer,
                dependencies.lunch_auto_chats,
            ),
            LunchAutoStatusCommand(
                messenger,
                common_error_renderer,
                dependencies.lunch_auto_chats,
            ),
        )
    )
    return CommandRuntime(catalog, flow_runner)
