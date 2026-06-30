from collections.abc import Callable
from datetime import datetime

from aiogram import Dispatcher

from office_food_bot.commands import create_command_router
from office_food_bot.config import Settings
from office_food_bot.database import Database
from office_food_bot.services import BotServices, build_services


def create_services(
    database: Database,
    settings: Settings,
    clock: Callable[[], datetime] | None = None,
) -> BotServices:
    return build_services(database, settings.telegram_admin_ids, settings.timezone, clock)


def create_dispatcher(services: BotServices) -> Dispatcher:
    dispatcher = Dispatcher(services=services)
    dispatcher.include_router(create_command_router())
    return dispatcher
