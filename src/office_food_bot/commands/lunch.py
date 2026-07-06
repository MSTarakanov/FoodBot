from __future__ import annotations

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices
from office_food_bot.services.lunch_auto import (
    LUNCH_ALL_ON_VACATION_TEXT,
    LunchPublishKind,
)

GROUP_CHAT_TYPES = frozenset({"group", "supergroup"})
GROUP_ONLY_MESSAGE = "Команда доступна только в групповом чате."


async def lunch_command(
    message: Message,
    bot: Bot,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    await state.clear()
    profile = telegram_profile_from_message(message)
    if profile is None:
        await messenger.reply(message, "Не вижу твой Telegram user id.")
        return

    block_reason = services.lunch.poll_block_reason(profile.telegram_user_id)
    if block_reason is not None:
        await messenger.reply(message, block_reason)
        return

    result = await services.lunch_publisher.publish(bot, message.chat.id)
    if result == LunchPublishKind.SKIPPED_ALL_ON_VACATION:
        await messenger.reply(message, LUNCH_ALL_ON_VACATION_TEXT)


async def lunch_auto_on_command(
    message: Message,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    await state.clear()
    if not _is_group_chat(message):
        await messenger.reply(message, GROUP_ONLY_MESSAGE)
        return

    services.lunch_auto_chats.enable(message.chat.id, message.chat.title)
    await messenger.reply(message, "Авто-ланч включен для этого чата.")


async def lunch_auto_off_command(
    message: Message,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    await state.clear()
    if not _is_group_chat(message):
        await messenger.reply(message, GROUP_ONLY_MESSAGE)
        return

    services.lunch_auto_chats.disable(message.chat.id)
    await messenger.reply(message, "Авто-ланч выключен для этого чата.")


async def lunch_auto_status_command(
    message: Message,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    await state.clear()
    if not _is_group_chat(message):
        await messenger.reply(message, GROUP_ONLY_MESSAGE)
        return

    await messenger.reply(message, services.lunch_auto_chats.status_text(message.chat.id))


def _is_group_chat(message: Message) -> bool:
    return str(message.chat.type) in GROUP_CHAT_TYPES
