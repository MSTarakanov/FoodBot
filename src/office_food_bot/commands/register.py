from __future__ import annotations

from aiogram import Bot
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.messaging import BotMessenger
from office_food_bot.models import (
    RegisteredUser,
    RegistrationDetails,
    RegistrationKind,
    SplitwiseConnection,
    SplitwiseMember,
    TelegramProfile,
)
from office_food_bot.services import BotServices
from office_food_bot.services.splitwise import SplitwiseLookupKind

NAME_PROMPT_TEXT = (
    "Напиши имя одним сообщением. Например: Максим\n"
    "Чтобы выйти из регистрации, отправь /cancel или запусти другую команду."
)
REGISTER_WITH_ARGUMENTS_TEXT = (
    "Регистрация теперь пошаговая: имя нужно прислать отдельным сообщением.\n"
    f"{NAME_PROMPT_TEXT}"
)
SPLITWISE_PROMPT_TEXT = (
    "Пришли email аккаунта Splitwise, чтобы я проверил тебя в офисной группе.\n"
    "Можно написать «Пропустить»."
)
SPLITWISE_SKIP_WARNING_TEXT = (
    "Splitwise не указан. Когда /balance будет подключен, она не сможет учитывать тебя "
    "без привязки."
)
SPLITWISE_SKIP_CHOICES = ("Пропустить",)
SPLITWISE_SKIP_ANSWERS = {"пропустить", "skip"}


class RegistrationFlow(StatesGroup):
    waiting_for_name = State()
    waiting_for_splitwise_email = State()
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
        await _reply_with_name_prompt(message, messenger, services, profile, NAME_PROMPT_TEXT)
        return

    await state.set_state(RegistrationFlow.waiting_for_name)
    await _reply_with_name_prompt(
        message,
        messenger,
        services,
        profile,
        REGISTER_WITH_ARGUMENTS_TEXT,
    )


async def _reply_with_name_prompt(
    message: Message,
    messenger: BotMessenger,
    services: BotServices,
    profile: TelegramProfile,
    text: str,
) -> None:
    suggested_display_name = services.registration.display_name_from_input(profile, "")
    await messenger.reply_with_choices(
        message,
        text,
        (suggested_display_name,),
        columns=1,
        one_time_keyboard=True,
    )


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

    profile = telegram_profile_from_message(message)
    if profile is None:
        await messenger.reply(message, "Не вижу твой Telegram user id.")
        return

    display_name = services.registration.display_name_from_input(profile, raw_display_name)
    await state.update_data(requested_display_name=display_name)
    await state.set_state(RegistrationFlow.waiting_for_splitwise_email)
    await messenger.reply_with_choices(
        message,
        f"Имя записал: {display_name}\n\n{SPLITWISE_PROMPT_TEXT}",
        SPLITWISE_SKIP_CHOICES,
        columns=1,
        one_time_keyboard=False,
    )


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


async def register_splitwise_email_message(
    message: Message,
    bot: Bot,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    raw_answer = message.text or ""
    requested_display_name = await _requested_display_name_from_state(state, messenger, message)
    if requested_display_name is None:
        return

    if _is_splitwise_skip(raw_answer):
        await _complete_registration(
            state,
            message,
            bot,
            messenger,
            services,
            requested_display_name,
            splitwise_member=None,
        )
        return

    result = await services.splitwise.find_member_by_email(raw_answer)
    if result.kind == SplitwiseLookupKind.FOUND and result.member is not None:
        await _complete_registration(
            state,
            message,
            bot,
            messenger,
            services,
            requested_display_name,
            splitwise_member=result.member,
        )
        return

    if result.kind == SplitwiseLookupKind.NOT_FOUND:
        await messenger.reply_with_choices(
            message,
            "Не нашел такой email в офисной Splitwise-группе.\n"
            "Проверь email и пришли другой или нажми «Пропустить».\n\n"
            f"{SPLITWISE_SKIP_WARNING_TEXT}",
            SPLITWISE_SKIP_CHOICES,
            columns=1,
            one_time_keyboard=False,
        )
        return

    await messenger.reply_with_choices(
        message,
        "Не смог проверить Splitwise прямо сейчас.\n"
        "Можно попробовать другой email позже или нажать «Пропустить».\n\n"
        f"{SPLITWISE_SKIP_WARNING_TEXT}",
        SPLITWISE_SKIP_CHOICES,
        columns=1,
        one_time_keyboard=False,
    )


async def registration_waiting_for_splitwise_unknown_message(
    message: Message,
    messenger: BotMessenger,
) -> None:
    await messenger.reply_with_choices(
        message,
        "Пришли email текстом или нажми «Пропустить».",
        SPLITWISE_SKIP_CHOICES,
        columns=1,
        one_time_keyboard=False,
    )


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

    splitwise_member = _splitwise_member_from_state_data(data)
    previous_details = _previous_details_from_state_data(data)
    user = services.registration.re_register(profile, requested_display_name, splitwise_member)
    await state.clear()
    await messenger.reply(
        message,
        _registration_reply_text(
            "Заявка на перерегистрацию отправлена. Жду аппрув.",
            splitwise_member,
        ),
        reply_markup=messenger.remove_keyboard(),
    )
    await _notify_admins_about_registration(
        bot,
        messenger,
        services,
        user,
        title="Перерегистрация:",
        splitwise_member=splitwise_member,
        previous_details=previous_details,
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
    *,
    splitwise_member: SplitwiseMember | None,
) -> None:
    profile = telegram_profile_from_message(message)
    if profile is None:
        await messenger.reply(message, "Не вижу твой Telegram user id.")
        return

    result = services.registration.register(profile, raw_display_name, splitwise_member)

    if result.kind == RegistrationKind.CREATED:
        await state.clear()
        await messenger.reply(
            message,
            _registration_reply_text(
                "Заявка на регистрацию отправлена. Жду аппрув.",
                splitwise_member,
            ),
            reply_markup=messenger.remove_keyboard(),
        )
        await _notify_admins_about_registration(
            bot,
            messenger,
            services,
            result.user,
            title="Новая регистрация:",
            splitwise_member=splitwise_member,
            previous_details=None,
        )
        return

    if result.kind == RegistrationKind.UPDATED_PENDING:
        await state.clear()
        await messenger.reply(
            message,
            _registration_reply_text("Заявка обновлена. Жду аппрув.", splitwise_member),
            reply_markup=messenger.remove_keyboard(),
        )
        await _notify_admins_about_registration(
            bot,
            messenger,
            services,
            result.user,
            title="Обновленная регистрация:",
            splitwise_member=splitwise_member,
            previous_details=result.previous_details,
        )
        return

    if result.kind == RegistrationKind.ALREADY_ACTIVE:
        previous_details = result.previous_details or RegistrationDetails(
            display_name=result.user.display_name,
            splitwise=None,
        )
        requested_details = _registration_details_from_input(
            services,
            profile,
            raw_display_name,
            splitwise_member,
        )
        if not _registration_details_changed(previous_details, requested_details):
            await state.clear()
            await messenger.reply(
                message,
                "Данные не изменились. Перерегистрацию не запускаю.",
                reply_markup=messenger.remove_keyboard(),
            )
            return

        await _ask_reregistration_confirmation(
            state,
            message,
            messenger,
            services,
            profile,
            result.user,
            raw_display_name,
            splitwise_member,
            previous_details,
        )
        return

    if result.kind == RegistrationKind.ALREADY_PENDING:
        await state.clear()
        await messenger.reply(
            message,
            f"Заявка уже ждет аппрува, {result.user.display_name}",
            reply_markup=messenger.remove_keyboard(),
        )
        return

    await state.clear()
    await messenger.reply(message, f"Регистрация сейчас недоступна, {result.user.display_name}")


async def _notify_admins_about_registration(
    bot: Bot,
    messenger: BotMessenger,
    services: BotServices,
    registered_user: RegisteredUser,
    *,
    title: str,
    splitwise_member: SplitwiseMember | None,
    previous_details: RegistrationDetails | None,
) -> None:
    current_details = _registration_details_from_user(registered_user, splitwise_member)
    for admin_id in services.registration.admin_ids:
        await messenger.try_send(
            bot,
            admin_id,
            _admin_registration_text(
                title,
                telegram_user_id=registered_user.telegram_user_id,
                current_details=current_details,
                previous_details=previous_details,
            ),
        )


async def _ask_reregistration_confirmation(
    state: FSMContext,
    message: Message,
    messenger: BotMessenger,
    services: BotServices,
    profile: TelegramProfile,
    user: RegisteredUser,
    raw_display_name: str,
    splitwise_member: SplitwiseMember | None,
    previous_details: RegistrationDetails,
) -> None:
    requested_display_name = services.registration.display_name_from_input(
        profile,
        raw_display_name,
    )
    await state.set_state(RegistrationFlow.confirming_reregistration)
    await state.update_data(
        requested_display_name=requested_display_name,
        requested_splitwise_user_id=_splitwise_user_id(splitwise_member),
        requested_splitwise_first_name=_splitwise_first_name(splitwise_member),
        requested_splitwise_last_name=_splitwise_last_name(splitwise_member),
        requested_splitwise_email=_splitwise_email(splitwise_member),
        previous_display_name=previous_details.display_name,
        previous_splitwise_user_id=_splitwise_connection_user_id(previous_details.splitwise),
        previous_splitwise_email=_splitwise_connection_email(previous_details.splitwise),
    )
    await messenger.reply_with_choices(
        message,
        "Вы уже зарегистрированы.\n"
        "Текущие данные:\n"
        f"Имя: {user.display_name}\n"
        f"Telegram ID: {user.telegram_user_id}\n"
        f"Username: {_username_text(user.username)}\n"
        f"{_splitwise_connection_admin_text(previous_details.splitwise)}\n"
        "\n"
        "Новые данные:\n"
        f"Имя: {requested_display_name}\n"
        f"{_splitwise_admin_text(splitwise_member)}\n"
        "\n"
        "Перерегистрировать вас?",
        ["Да", "Нет"],
    )


def _username_text(username: str | None) -> str:
    if username is None:
        return "не указан"
    return f"@{username}"


async def _requested_display_name_from_state(
    state: FSMContext,
    messenger: BotMessenger,
    message: Message,
) -> str | None:
    data = await state.get_data()
    requested_display_name = data.get("requested_display_name")
    if isinstance(requested_display_name, str):
        return requested_display_name

    await state.clear()
    await messenger.reply(
        message,
        "Не нашел имя для регистрации. Запусти /register заново.",
        reply_markup=messenger.remove_keyboard(),
    )
    return None


def _registration_reply_text(base_text: str, splitwise_member: SplitwiseMember | None) -> str:
    if splitwise_member is not None:
        return (
            f"{base_text}\n\n"
            f"Splitwise найден: {splitwise_member.email} "
            f"(ID {splitwise_member.splitwise_user_id})."
        )
    return f"{base_text}\n\n{SPLITWISE_SKIP_WARNING_TEXT}"


def _splitwise_admin_text(splitwise_member: SplitwiseMember | None) -> str:
    return _splitwise_connection_admin_text(_splitwise_connection_from_member(splitwise_member))


def _splitwise_connection_admin_text(splitwise: SplitwiseConnection | None) -> str:
    return f"Splitwise: {_splitwise_value_text(splitwise)}"


def _splitwise_value_text(splitwise: SplitwiseConnection | None) -> str:
    if splitwise is None:
        return "не указан"
    return f"{splitwise.email} (ID {splitwise.splitwise_user_id})"


def _admin_registration_text(
    title: str,
    *,
    telegram_user_id: int,
    current_details: RegistrationDetails,
    previous_details: RegistrationDetails | None,
) -> str:
    if previous_details is None:
        return (
            f"{title}\n"
            f"Имя: {current_details.display_name}\n"
            f"Telegram ID: {telegram_user_id}\n"
            f"{_splitwise_connection_admin_text(current_details.splitwise)}\n"
            f"Аппрув: /approve {telegram_user_id}"
        )

    change_lines = _registration_change_lines(previous_details, current_details)
    return "\n".join(
        (
            title,
            f"Telegram ID: {telegram_user_id}",
            "Изменения:",
            *change_lines,
            f"Аппрув: /approve {telegram_user_id}",
        )
    )


def _registration_change_lines(
    previous_details: RegistrationDetails,
    current_details: RegistrationDetails,
) -> tuple[str, ...]:
    lines: list[str] = []
    if previous_details.display_name != current_details.display_name:
        lines.extend(
            (
                "Имя:",
                f"Было: {previous_details.display_name}",
                f"Стало: {current_details.display_name}",
            )
        )
    if not _same_splitwise_connection(previous_details.splitwise, current_details.splitwise):
        if lines:
            lines.append("")
        lines.extend(
            (
                "Splitwise:",
                f"Было: {_splitwise_value_text(previous_details.splitwise)}",
                f"Стало: {_splitwise_value_text(current_details.splitwise)}",
            )
        )
    if not lines:
        return ("Нет изменений.",)
    return tuple(lines)


def _registration_details_from_user(
    user: RegisteredUser,
    splitwise_member: SplitwiseMember | None,
) -> RegistrationDetails:
    return RegistrationDetails(
        display_name=user.display_name,
        splitwise=_splitwise_connection_from_member(splitwise_member),
    )


def _registration_details_from_input(
    services: BotServices,
    profile: TelegramProfile,
    raw_display_name: str,
    splitwise_member: SplitwiseMember | None,
) -> RegistrationDetails:
    return RegistrationDetails(
        display_name=services.registration.display_name_from_input(profile, raw_display_name),
        splitwise=_splitwise_connection_from_member(splitwise_member),
    )


def _registration_details_changed(
    previous_details: RegistrationDetails,
    current_details: RegistrationDetails,
) -> bool:
    return (
        previous_details.display_name != current_details.display_name
        or not _same_splitwise_connection(previous_details.splitwise, current_details.splitwise)
    )


def _same_splitwise_connection(
    first: SplitwiseConnection | None,
    second: SplitwiseConnection | None,
) -> bool:
    if first is None or second is None:
        return first is None and second is None
    return (
        first.splitwise_user_id == second.splitwise_user_id
        and first.email.casefold() == second.email.casefold()
    )


def _splitwise_connection_from_member(
    splitwise_member: SplitwiseMember | None,
) -> SplitwiseConnection | None:
    if splitwise_member is None:
        return None
    return SplitwiseConnection(
        splitwise_user_id=splitwise_member.splitwise_user_id,
        email=splitwise_member.email,
    )


def _is_splitwise_skip(raw_answer: str) -> bool:
    return raw_answer.strip().lower() in SPLITWISE_SKIP_ANSWERS


def _splitwise_user_id(splitwise_member: SplitwiseMember | None) -> int | None:
    if splitwise_member is None:
        return None
    return splitwise_member.splitwise_user_id


def _splitwise_first_name(splitwise_member: SplitwiseMember | None) -> str | None:
    if splitwise_member is None:
        return None
    return splitwise_member.first_name


def _splitwise_last_name(splitwise_member: SplitwiseMember | None) -> str | None:
    if splitwise_member is None:
        return None
    return splitwise_member.last_name


def _splitwise_email(splitwise_member: SplitwiseMember | None) -> str | None:
    if splitwise_member is None:
        return None
    return splitwise_member.email


def _splitwise_connection_user_id(splitwise: SplitwiseConnection | None) -> int | None:
    if splitwise is None:
        return None
    return splitwise.splitwise_user_id


def _splitwise_connection_email(splitwise: SplitwiseConnection | None) -> str | None:
    if splitwise is None:
        return None
    return splitwise.email


def _previous_details_from_state_data(data: dict[str, object]) -> RegistrationDetails | None:
    raw_display_name = data.get("previous_display_name")
    if not isinstance(raw_display_name, str):
        return None

    return RegistrationDetails(
        display_name=raw_display_name,
        splitwise=_splitwise_connection_from_state_data(data),
    )


def _splitwise_connection_from_state_data(
    data: dict[str, object],
) -> SplitwiseConnection | None:
    raw_user_id = data.get("previous_splitwise_user_id")
    raw_email = data.get("previous_splitwise_email")
    if not isinstance(raw_user_id, int) or not isinstance(raw_email, str):
        return None

    return SplitwiseConnection(
        splitwise_user_id=raw_user_id,
        email=raw_email,
    )


def _splitwise_member_from_state_data(data: dict[str, object]) -> SplitwiseMember | None:
    raw_user_id = data.get("requested_splitwise_user_id")
    raw_email = data.get("requested_splitwise_email")
    if not isinstance(raw_user_id, int) or not isinstance(raw_email, str):
        return None

    raw_first_name = data.get("requested_splitwise_first_name")
    raw_last_name = data.get("requested_splitwise_last_name")
    first_name = raw_first_name if isinstance(raw_first_name, str) else ""
    last_name = raw_last_name if isinstance(raw_last_name, str) else None

    return SplitwiseMember(
        splitwise_user_id=raw_user_id,
        first_name=first_name,
        last_name=last_name,
        email=raw_email,
    )
