import asyncio

from aiogram import Bot

from office_food_bot.app import create_dispatcher, create_services
from office_food_bot.commands import setup_bot_commands
from office_food_bot.config import load_settings
from office_food_bot.database import Database


async def main() -> None:
    settings = load_settings()
    database = Database(settings.database_path)
    database.init_schema()
    services = create_services(database, settings)
    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = create_dispatcher(services)
    try:
        await setup_bot_commands(bot, services.registration.admin_ids)
        await dispatcher.start_polling(bot)
    finally:
        database.close()


def run() -> None:
    asyncio.run(main())
