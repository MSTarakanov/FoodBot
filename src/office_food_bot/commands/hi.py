from __future__ import annotations

import logging

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices

logger = logging.getLogger(__name__)


async def hi_command(
    message: Message,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    await state.clear()
    logger.warning(
        "/hi handled by @%s: chat_id=%s, telegram_user_id=%s",
        services.telegram_bot_username,
        message.chat.id,
        message.from_user.id if message.from_user is not None else None,
    )
    await messenger.reply(message, "Привет! Я на месте.")
