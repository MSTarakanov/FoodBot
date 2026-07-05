from __future__ import annotations

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commands.access import ensure_command_allowed
from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.messaging import BotMessenger
from office_food_bot.models import PendingRegistration, RegisteredUser, SplitwiseConnection
from office_food_bot.services import BotServices


async def register_requests_list_command(
    message: Message,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    if not await ensure_command_allowed(
        message,
        "register_requests_list",
        messenger,
        services,
        state,
    ):
        return

    await state.clear()
    profile = telegram_profile_from_message(message)
    if profile is None:
        await messenger.reply(message, "Не вижу твой Telegram user id.")
        return

    if not services.registration.can_approve(profile.telegram_user_id):
        await messenger.reply(message, "Не могу: список заявок доступен только админам.")
        return

    pending_users = services.registration.list_pending_requests(profile.telegram_user_id)
    if not pending_users:
        await messenger.reply(message, "Заявок на регистрацию нет.")
        return

    await messenger.reply(message, _pending_requests_text(pending_users))


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
