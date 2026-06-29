from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message


async def start_command(message: Message) -> None:
    await message.answer(
        "Привет! Я офисный бот про еду. Пока умею команды /start и /hi."
    )


async def hi_command(message: Message) -> None:
    await message.answer("Привет! Я на месте.")


def create_command_router() -> Router:
    router = Router(name="commands")
    router.message.register(start_command, CommandStart())
    router.message.register(hi_command, Command("hi"))
    return router
