import asyncio
import logging
from pathlib import Path

from aiogram import Bot

from office_food_bot.app import create_application, create_services
from office_food_bot.commanding.menu import setup_bot_commands
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
        application = create_application(services)
        dispatcher = application.dispatcher
        await setup_bot_commands(bot, services.command_access, application.commands)
        services.lunch_scheduler.register_job(bot)
        await services.coffee.restore_jobs(bot)
        services.job_scheduler.start()
        logger.info(
            "Bot started: username=@%s, environment=%s, database=%s, "
            "schema_version=%s, timezone=%s",
            settings.telegram_bot_username,
            settings.environment.value,
            settings.database_path,
            database.schema_version(),
            settings.timezone,
        )
        await dispatcher.start_polling(bot)
    finally:
        if services is not None:
            services.job_scheduler.shutdown()
        if database is not None:
            database.close()
        await bot.session.close()


def run() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    try:
        asyncio.run(main())
    except ProductionTokenInDevelopmentError as error:
        raise SystemExit(str(error)) from None
