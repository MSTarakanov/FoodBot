from __future__ import annotations

from aiogram.types import Message


async def start_command(message: Message) -> None:
    await message.answer(
        "Привет! Я офисный бот про еду. Умею /register, /meta, /balance и /hi."
    )
