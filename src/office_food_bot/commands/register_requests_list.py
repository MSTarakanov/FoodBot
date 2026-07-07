from __future__ import annotations

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.messaging import BotMessenger
from office_food_bot.models import (
    PendingRegistration,
    RegisteredUser,
    SeenTelegramAccount,
    SplitwiseConnection,
)
from office_food_bot.services import BotServices


async def register_requests_list_command(
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

    if not services.registration.can_approve(profile.telegram_user_id):
        await messenger.reply(message, "Не могу: список заявок доступен только админам.")
        return

    pending_requests = services.registration.list_pending_requests(profile.telegram_user_id)
    seen_accounts = services.registration.list_unregistered_seen_accounts(
        profile.telegram_user_id,
    )
    if not pending_requests and not seen_accounts:
        await messenger.reply(message, "Заявок на регистрацию нет.")
        return

    await messenger.reply(message, _registration_requests_text(pending_requests, seen_accounts))


def _registration_requests_text(
    pending_requests: tuple[PendingRegistration, ...],
    seen_accounts: tuple[SeenTelegramAccount, ...],
) -> str:
    lines: list[str] = []
    if pending_requests:
        lines.append(_pending_requests_text(pending_requests))
    else:
        lines.append("Заявок на регистрацию нет.")

    if seen_accounts:
        lines.extend(("", _seen_accounts_registration_text(seen_accounts)))

    return "\n".join(lines)


def _pending_requests_text(pending_users: tuple[PendingRegistration, ...]) -> str:
    lines = ["Заявки на регистрацию:"]
    for index, registration in enumerate(pending_users, start=1):
        user = registration.user
        username = _telegram_username_text(user)
        lines.append(
            f"{index}. {user.display_name}{username} - "
            f"Telegram ID {user.telegram_user_id} - "
            f"{_splitwise_text(registration.splitwise)} - "
            f"/approve {user.telegram_user_id}"
        )
    return "\n".join(lines)


def _telegram_username_text(user: RegisteredUser) -> str:
    if user.username is None:
        return ""
    return f" (@{user.username})"


def _splitwise_text(splitwise: SplitwiseConnection | None) -> str:
    if splitwise is None:
        return "Splitwise: не указан"
    return f"Splitwise: {splitwise.email} (ID {splitwise.splitwise_user_id})"


def _seen_accounts_registration_text(seen_accounts: tuple[SeenTelegramAccount, ...]) -> str:
    lines = ["Видел незарегистрированных пользователей:"]
    for index, seen_account in enumerate(seen_accounts, start=1):
        lines.append(
            f"{index}. {_seen_account_display_text(seen_account)} - "
            f"Telegram ID {seen_account.telegram_user_id} - "
            f"/register {seen_account.telegram_user_id}"
        )
    return "\n".join(lines)


def _seen_account_display_text(seen_account: SeenTelegramAccount) -> str:
    display_name = " ".join(
        part for part in (seen_account.first_name, seen_account.last_name) if part is not None
    )
    if seen_account.username is None:
        return display_name
    return f"{display_name} (@{seen_account.username})"
