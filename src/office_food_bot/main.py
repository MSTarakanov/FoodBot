import asyncio

from aiogram import Bot

from office_food_bot.app import create_dispatcher
from office_food_bot.config import load_settings


async def main() -> None:
    settings = load_settings()
    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = create_dispatcher()
    await dispatcher.start_polling(bot)


def run() -> None:
    asyncio.run(main())
