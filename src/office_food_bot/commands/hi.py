from __future__ import annotations

from aiogram.types import Message


async def hi_command(message: Message) -> None:
    await message.answer("Привет! Я на месте.")
