from __future__ import annotations

from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import LinkPreviewOptions, Message

from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices


async def balance_command(
    message: Message,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    await state.clear()
    profile = telegram_profile_from_message(message)
    if profile is None:
        await messenger.reply(message, "Не вижу твой Telegram user id.")
        return

    await messenger.reply(
        message,
        await services.balances.balance(profile.telegram_user_id),
        parse_mode=ParseMode.HTML,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
