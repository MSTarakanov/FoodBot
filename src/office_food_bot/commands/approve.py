from __future__ import annotations

from contextlib import suppress

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.filters.command import CommandObject
from aiogram.types import Message

from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.services import BotServices


async def approve_command(
    message: Message,
    command: CommandObject,
    bot: Bot,
    services: BotServices,
) -> None:
    approver = telegram_profile_from_message(message)
    if approver is None:
        await message.answer("Не вижу твой Telegram user id.")
        return

    if not command.args:
        await message.answer("Напиши Telegram user id: /approve 123456789")
        return

    try:
        telegram_user_id = int(command.args.strip())
    except ValueError:
        await message.answer("Telegram user id должен быть числом: /approve 123456789")
        return

    result = services.registration.approve(approver.telegram_user_id, telegram_user_id)
    if result.kind == "forbidden":
        await message.answer("Не могу: аппрувить могут только админы.")
        return

    if result.kind == "not_found":
        await message.answer(f"Не нашел заявку для Telegram ID {telegram_user_id}.")
        return

    approved_user = result.user
    if approved_user is None:
        msg = "Approved user is unexpectedly missing"
        raise RuntimeError(msg)

    await message.answer(f"Аппрувнул: {approved_user.display_name}")
    with suppress(TelegramAPIError):
        await bot.send_message(
            telegram_user_id,
            f"Регистрация подтверждена. Теперь я буду звать тебя {approved_user.display_name}.",
        )
