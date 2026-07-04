import asyncio
from pathlib import Path

from aiogram import Bot

from office_food_bot.app import create_dispatcher, create_services
from office_food_bot.commands import setup_bot_commands
from office_food_bot.config import load_settings
from office_food_bot.database import Database
from office_food_bot.runtime_guard import (
    ProductionTokenInDevelopmentError,
    ensure_safe_telegram_token_for_environment,
)


async def main() -> None:
    settings = load_settings()
    bot = Bot(token=settings.telegram_bot_token)
    database: Database | None = None
    try:
        await ensure_safe_telegram_token_for_environment(settings, bot)
        database = Database(Path(settings.database_path))
        database.init_schema()
        services = create_services(database, settings)
        dispatcher = create_dispatcher(services)
        await setup_bot_commands(bot, services.registration.admin_ids)
        await dispatcher.start_polling(bot)
    finally:
        if database is not None:
            database.close()
        await bot.session.close()


def run() -> None:
    try:
        asyncio.run(main())
    except ProductionTokenInDevelopmentError as error:
        raise SystemExit(str(error)) from None
