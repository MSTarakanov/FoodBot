from __future__ import annotations

from aiogram import Bot
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.messaging import BotMessenger
from office_food_bot.models import RegisteredUser, RegistrationKind, TelegramProfile
from office_food_bot.services import BotServices


class RegistrationFlow(StatesGroup):
    waiting_for_name = State()
    confirming_reregistration = State()


async def register_command(
    message: Message,
    command: CommandObject,
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

    if not command.args:
        await state.set_state(RegistrationFlow.waiting_for_name)
        await messenger.reply(
            message,
            "Напиши имя одним сообщением. Например: Максим\n"
            "Чтобы выйти из регистрации, отправь /cancel или запусти другую команду.",
        )
        return

    await _complete_registration(state, message, bot, messenger, services, command.args)


async def register_name_message(
    message: Message,
    bot: Bot,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    raw_display_name = message.text or ""
    if not raw_display_name.strip():
        await messenger.reply(message, "Имя не может быть пустым. Напиши имя, например: Максим")
        return

    await state.clear()
    await _complete_registration(state, message, bot, messenger, services, raw_display_name)


async def cancel_registration_command(
    message: Message,
    messenger: BotMessenger,
    state: FSMContext,
) -> None:
    if await state.get_state() is None:
        await messenger.reply(message, "Нет активного сценария.")
        return

    await state.clear()
    await messenger.reply(
        message,
        "Текущий сценарий отменен.",
        reply_markup=messenger.remove_keyboard(),
    )


async def registration_waiting_for_name_unknown_message(
    message: Message,
    messenger: BotMessenger,
) -> None:
    await messenger.reply(message, "Напиши имя текстом. Например: Максим")


async def confirm_reregistration_message(
    message: Message,
    bot: Bot,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    answer = (message.text or "").strip().lower()
    if answer not in {"да", "yes", "y", "нет", "no", "n"}:
        await messenger.reply_with_choices(
            message,
            "Выбери: перерегистрировать вас?",
            ["Да", "Нет"],
        )
        return

    if answer in {"нет", "no", "n"}:
        await state.clear()
        await messenger.reply(
            message,
            "Оставил текущую регистрацию.",
            reply_markup=messenger.remove_keyboard(),
        )
        return

    profile = telegram_profile_from_message(message)
    if profile is None:
        await messenger.reply(message, "Не вижу твой Telegram user id.")
        return

    data = await state.get_data()
    requested_display_name = data.get("requested_display_name")
    if not isinstance(requested_display_name, str):
        await state.clear()
        await messenger.reply(
            message,
            "Не нашел данные для перерегистрации. Запусти /register заново.",
            reply_markup=messenger.remove_keyboard(),
        )
        return

    user = services.registration.re_register(profile, requested_display_name)
    await state.clear()
    await messenger.reply(
        message,
        "Заявка на перерегистрацию отправлена. Жду аппрув.",
        reply_markup=messenger.remove_keyboard(),
    )
    await _notify_admins_about_registration(
        bot,
        messenger,
        services,
        user,
        title="Перерегистрация:",
    )


async def confirm_reregistration_unknown_message(
    message: Message,
    messenger: BotMessenger,
) -> None:
    await messenger.reply_with_choices(
        message,
        "Выбери: перерегистрировать вас?",
        ["Да", "Нет"],
    )


async def _complete_registration(
    state: FSMContext,
    message: Message,
    bot: Bot,
    messenger: BotMessenger,
    services: BotServices,
    raw_display_name: str,
) -> None:
    profile = telegram_profile_from_message(message)
    if profile is None:
        await messenger.reply(message, "Не вижу твой Telegram user id.")
        return

    result = services.registration.register(profile, raw_display_name)

    if result.kind == RegistrationKind.CREATED:
        await messenger.reply(message, "Заявка на регистрацию отправлена. Жду аппрув.")
        await _notify_admins_about_registration(
            bot,
            messenger,
            services,
            result.user,
            title="Новая регистрация:",
        )
        return

    if result.kind == RegistrationKind.UPDATED_PENDING:
        await messenger.reply(message, "Заявка обновлена. Жду аппрув.")
        await _notify_admins_about_registration(
            bot,
            messenger,
            services,
            result.user,
            title="Обновленная регистрация:",
        )
        return

    if result.kind == RegistrationKind.ALREADY_ACTIVE:
        await _ask_reregistration_confirmation(
            state,
            message,
            messenger,
            services,
            profile,
            result.user,
            raw_display_name,
        )
        return

    if result.kind == RegistrationKind.ALREADY_PENDING:
        await messenger.reply(message, f"Заявка уже ждет аппрува, {result.user.display_name}")
        return

    await messenger.reply(message, f"Регистрация сейчас недоступна, {result.user.display_name}")


async def _notify_admins_about_registration(
    bot: Bot,
    messenger: BotMessenger,
    services: BotServices,
    registered_user: RegisteredUser,
    *,
    title: str,
) -> None:
    for admin_id in services.registration.admin_ids:
        await messenger.try_send(
            bot,
            admin_id,
            f"{title}\n"
            f"Имя: {registered_user.display_name}\n"
            f"Telegram ID: {registered_user.telegram_user_id}\n"
            f"Аппрув: /approve {registered_user.telegram_user_id}",
        )


async def _ask_reregistration_confirmation(
    state: FSMContext,
    message: Message,
    messenger: BotMessenger,
    services: BotServices,
    profile: TelegramProfile,
    user: RegisteredUser,
    raw_display_name: str,
) -> None:
    requested_display_name = services.registration.display_name_from_input(
        profile,
        raw_display_name,
    )
    await state.set_state(RegistrationFlow.confirming_reregistration)
    await state.update_data(requested_display_name=requested_display_name)
    await messenger.reply_with_choices(
        message,
        "Вы уже зарегистрированы.\n"
        "Текущие данные:\n"
        f"Имя: {user.display_name}\n"
        f"Telegram ID: {user.telegram_user_id}\n"
        f"Username: {_username_text(user.username)}\n"
        "\n"
        "Новые данные:\n"
        f"Имя: {requested_display_name}\n"
        "\n"
        "Перерегистрировать вас?",
        ["Да", "Нет"],
    )


def _username_text(username: str | None) -> str:
    if username is None:
        return "не указан"
    return f"@{username}"
