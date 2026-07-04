from __future__ import annotations

from aiogram import Bot
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.messaging import BotMessenger
from office_food_bot.models import ApprovalKind
from office_food_bot.services import BotServices


async def approve_command(
    message: Message,
    command: CommandObject,
    bot: Bot,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    await state.clear()
    approver = telegram_profile_from_message(message)
    if approver is None:
        await messenger.reply(message, "Не вижу твой Telegram user id.")
        return

    if not command.args:
        await messenger.reply(message, "Напиши Telegram user id: /approve 123456789")
        return

    try:
        telegram_user_id = int(command.args.strip())
    except ValueError:
        await messenger.reply(message, "Telegram user id должен быть числом: /approve 123456789")
        return

    result = services.registration.approve(approver.telegram_user_id, telegram_user_id)
    if result.kind == ApprovalKind.FORBIDDEN:
        await messenger.reply(message, "Не могу: аппрувить могут только админы.")
        return

    if result.kind == ApprovalKind.NOT_FOUND:
        await messenger.reply(message, f"Не нашел заявку для Telegram ID {telegram_user_id}.")
        return

    approved_user = result.user
    if approved_user is None:
        msg = "Approved user is unexpectedly missing"
        raise RuntimeError(msg)

    await messenger.reply(message, f"Аппрувнул: {approved_user.display_name}")
    await messenger.try_send(
        bot,
        telegram_user_id,
        f"Регистрация подтверждена. Теперь я буду звать тебя {approved_user.display_name}.",
    )
