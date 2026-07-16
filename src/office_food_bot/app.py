from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from office_food_bot.commanding.catalog import CommandCatalog
from office_food_bot.commanding.errors.handler import unhandled_error_handler
from office_food_bot.commanding.errors.rendering import build_user_error_renderer
from office_food_bot.commands.factory import build_command_runtime
from office_food_bot.commands.router import create_command_router
from office_food_bot.config import Settings
from office_food_bot.database import Database
from office_food_bot.services import BotServices, build_services
from office_food_bot.services.splitwise import SplitwiseGroupClient


def create_services(
    database: Database,
    settings: Settings,
    clock: Callable[[], datetime] | None = None,
    splitwise_client: SplitwiseGroupClient | None = None,
) -> BotServices:
    return build_services(
        database,
        settings.telegram_bot_username,
        settings.telegram_admin_ids,
        settings.timezone,
        settings.splitwise_api_key,
        settings.splitwise_group_id,
        clock,
        splitwise_client,
    )


@dataclass(frozen=True)
class BotApplication:
    dispatcher: Dispatcher
    commands: CommandCatalog


def create_application(services: BotServices) -> BotApplication:
    messenger = services.messenger
    command_runtime = build_command_runtime(services)
    error_renderer = build_user_error_renderer()
    dispatcher = Dispatcher(
        storage=MemoryStorage(),
        messenger=messenger,
        user_error_renderer=error_renderer,
    )
    dispatcher.errors.register(unhandled_error_handler)
    dispatcher.include_router(
        create_command_router(
            services,
            command_runtime.catalog,
            error_renderer,
            command_runtime.flow_runner,
        )
    )
    return BotApplication(dispatcher, command_runtime.catalog)


def create_dispatcher(services: BotServices) -> Dispatcher:
    return create_application(services).dispatcher
