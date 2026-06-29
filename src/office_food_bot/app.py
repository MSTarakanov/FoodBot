from aiogram import Dispatcher

from office_food_bot.handlers import create_command_router


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(create_command_router())
    return dispatcher
