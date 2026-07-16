from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from office_food_bot.bootstrap import BotDependencies, build_dependencies
from office_food_bot.commanding.catalog import CommandCatalog
from office_food_bot.commanding.errors.handler import unhandled_error_handler
from office_food_bot.commanding.errors.rendering import (
    CommonErrorRenderer,
    InternalErrorRenderer,
)
from office_food_bot.commands.factory import build_command_runtime
from office_food_bot.commands.router import create_command_router
from office_food_bot.config import Settings
from office_food_bot.database import Database
from office_food_bot.integrations.splitwise import SplitwiseGroupClient


def create_dependencies(
    database: Database,
    settings: Settings,
    clock: Callable[[], datetime] | None = None,
    splitwise_client: SplitwiseGroupClient | None = None,
) -> BotDependencies:
    return build_dependencies(
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


def create_application(dependencies: BotDependencies) -> BotApplication:
    messenger = dependencies.messenger
    common_error_renderer = CommonErrorRenderer(dependencies.telegram_bot_username)
    command_runtime = build_command_runtime(dependencies, common_error_renderer)
    dispatcher = Dispatcher(
        storage=MemoryStorage(),
        messenger=messenger,
        internal_error_renderer=InternalErrorRenderer(),
    )
    dispatcher.errors.register(unhandled_error_handler)
    dispatcher.include_router(
        create_command_router(
            dependencies,
            command_runtime.catalog,
            common_error_renderer,
            command_runtime.flow_runner,
        )
    )
    return BotApplication(dispatcher, command_runtime.catalog)


def create_dispatcher(dependencies: BotDependencies) -> Dispatcher:
    return create_application(dependencies).dispatcher
