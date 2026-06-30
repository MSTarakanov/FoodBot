from __future__ import annotations

from contextlib import suppress

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.filters.command import CommandObject
from aiogram.types import Message

from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.models import RegisteredUser, RegistrationKind
from office_food_bot.services import BotServices


async def register_command(
    message: Message,
    command: CommandObject,
    bot: Bot,
    services: BotServices,
) -> None:
    profile = telegram_profile_from_message(message)
    if profile is None:
        await message.answer("Не вижу твой Telegram user id.")
        return

    if not command.args:
        await message.answer("Напиши имя: /register Максим")
        return

    result = services.registration.register(profile, command.args)

    if result.kind == RegistrationKind.CREATED:
        await message.answer("Заявка на регистрацию отправлена. Жду аппрув.")
        await _notify_admins_about_registration(bot, services, result.user)
        return

    if result.kind == RegistrationKind.ALREADY_ACTIVE:
        await message.answer(f"Уже зарегистрирован, {result.user.display_name}")
        return

    if result.kind == RegistrationKind.ALREADY_PENDING:
        await message.answer(f"Заявка уже ждет аппрува, {result.user.display_name}")
        return

    await message.answer(f"Регистрация сейчас недоступна, {result.user.display_name}")


async def _notify_admins_about_registration(
    bot: Bot,
    services: BotServices,
    registered_user: RegisteredUser,
) -> None:
    for admin_id in services.registration.admin_ids:
        if admin_id == registered_user.telegram_user_id:
            continue
        with suppress(TelegramAPIError):
            await bot.send_message(
                admin_id,
                "Новая регистрация:\n"
                f"Имя: {registered_user.display_name}\n"
                f"Telegram ID: {registered_user.telegram_user_id}\n"
                f"Аппрув: /approve {registered_user.telegram_user_id}",
            )
