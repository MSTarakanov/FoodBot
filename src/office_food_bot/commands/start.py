from __future__ import annotations

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commands.access import ensure_command_allowed
from office_food_bot.commands.definitions import START_TEXT
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices


async def start_command(
    message: Message,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    if not await ensure_command_allowed(message, "start", messenger, services, state):
        return

    await state.clear()
    await messenger.reply(message, START_TEXT)
