import asyncio
import logging
from pathlib import Path

from aiogram import Bot

from office_food_bot.app import create_application, create_dependencies
from office_food_bot.bootstrap import BotDependencies
from office_food_bot.commanding.menu import setup_bot_commands
from office_food_bot.config import load_settings
from office_food_bot.database import Database
from office_food_bot.runtime_guard import (
    ProductionTokenInDevelopmentError,
    ensure_safe_telegram_token_for_environment,
)

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = load_settings()
    bot = Bot(token=settings.telegram_bot_token)
    database: Database | None = None
    dependencies: BotDependencies | None = None
    try:
        await ensure_safe_telegram_token_for_environment(settings, bot)
        database = Database(Path(settings.database_path))
        database.init_schema()
        dependencies = create_dependencies(database, settings)
        application = create_application(dependencies)
        dispatcher = application.dispatcher
        await setup_bot_commands(bot, dependencies.command_access, application.commands)
        dependencies.lunch_scheduler.register_job(bot)
        await dependencies.coffee.restore_jobs(bot)
        dependencies.job_scheduler.start()
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
        if dependencies is not None:
            dependencies.job_scheduler.shutdown()
        if database is not None:
            database.close()
        await bot.session.close()


def run() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    try:
        asyncio.run(main())
    except ProductionTokenInDevelopmentError as error:
        raise SystemExit(str(error)) from None
