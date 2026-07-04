from collections.abc import Callable
from datetime import datetime

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from office_food_bot.commands import create_command_router
from office_food_bot.config import Settings
from office_food_bot.database import Database
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices, build_services


def create_services(
    database: Database,
    settings: Settings,
    clock: Callable[[], datetime] | None = None,
) -> BotServices:
    return build_services(database, settings.telegram_admin_ids, settings.timezone, clock)


def create_dispatcher(services: BotServices) -> Dispatcher:
    dispatcher = Dispatcher(
        storage=MemoryStorage(),
        services=services,
        messenger=BotMessenger(),
    )
    dispatcher.include_router(create_command_router())
    return dispatcher
