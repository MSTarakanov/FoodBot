from __future__ import annotations

from contextlib import suppress

from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import Message

from office_food_bot.repositories import RegisteredUser, TelegramProfile
from office_food_bot.services import BotServices


async def start_command(message: Message) -> None:
    await message.answer(
        "Привет! Я офисный бот про еду. Умею /register, /meta, /balance и /hi."
    )


async def hi_command(message: Message) -> None:
    await message.answer("Привет! Я на месте.")


async def register_command(
    message: Message,
    command: CommandObject,
    bot: Bot,
    services: BotServices,
) -> None:
    profile = _telegram_profile_from_message(message)
    if profile is None:
        await message.answer("Не вижу твой Telegram user id.")
        return

    if not command.args:
        await message.answer("Напиши имя: /register Максим")
        return

    result = services.registration.register(profile, command.args)

    if result.kind == "created":
        await message.answer("Заявка на регистрацию отправлена. Жду аппрув.")
        await _notify_admins_about_registration(bot, services, result.user)
        return

    if result.kind == "already_active":
        await message.answer(f"Уже зарегистрирован, {result.user.display_name}")
        return

    if result.kind == "already_pending":
        await message.answer(f"Заявка уже ждет аппрува, {result.user.display_name}")
        return

    await message.answer(f"Регистрация сейчас недоступна, {result.user.display_name}")


async def approve_command(
    message: Message,
    command: CommandObject,
    bot: Bot,
    services: BotServices,
) -> None:
    approver = _telegram_profile_from_message(message)
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


async def meta_command(
    message: Message,
    command: CommandObject,
    services: BotServices,
) -> None:
    profile = _telegram_profile_from_message(message)
    if profile is None:
        await message.answer("Не вижу твой Telegram user id.")
        return

    if not command.args:
        await message.answer("Напиши через сколько минут: /meta 25")
        return

    await message.answer(services.presence.meta(profile.telegram_user_id, command.args))


async def balance_command(message: Message, services: BotServices) -> None:
    profile = _telegram_profile_from_message(message)
    if profile is None:
        await message.answer("Не вижу твой Telegram user id.")
        return

    await message.answer(services.balances.balance(profile.telegram_user_id))


def create_command_router() -> Router:
    router = Router(name="commands")
    router.message.register(start_command, CommandStart())
    router.message.register(hi_command, Command("hi"))
    router.message.register(register_command, Command("register"))
    router.message.register(approve_command, Command("approve"))
    router.message.register(meta_command, Command("meta"))
    router.message.register(balance_command, Command("balance"))
    return router


def _telegram_profile_from_message(message: Message) -> TelegramProfile | None:
    if message.from_user is None:
        return None

    return TelegramProfile(
        telegram_user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )


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
