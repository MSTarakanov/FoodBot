import asyncio
import logging
from pathlib import Path

from aiogram import Bot

from office_food_bot.app import create_dispatcher, create_services
from office_food_bot.commands.menu import setup_bot_commands
from office_food_bot.config import load_settings
from office_food_bot.database import Database
from office_food_bot.runtime_guard import (
    ProductionTokenInDevelopmentError,
    ensure_safe_telegram_token_for_environment,
)
from office_food_bot.services import BotServices

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = load_settings()
    bot = Bot(token=settings.telegram_bot_token)
    database: Database | None = None
    services: BotServices | None = None
    try:
        await ensure_safe_telegram_token_for_environment(settings, bot)
        database = Database(Path(settings.database_path))
        database.init_schema()
        services = create_services(database, settings)
        dispatcher = create_dispatcher(services)
        await setup_bot_commands(bot, services.command_access)
        services.lunch_scheduler.start(bot)
        logger.info(
            "Bot started: username=@%s, environment=%s, database=%s, timezone=%s",
            settings.telegram_bot_username,
            settings.environment.value,
            settings.database_path,
            settings.timezone,
        )
        await dispatcher.start_polling(bot)
    finally:
        if services is not None:
            services.lunch_scheduler.shutdown()
        if database is not None:
            database.close()
        await bot.session.close()


def run() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    try:
        asyncio.run(main())
    except ProductionTokenInDevelopmentError as error:
        raise SystemExit(str(error)) from None
