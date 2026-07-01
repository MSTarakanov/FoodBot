from __future__ import annotations

from aiogram.types import Message

from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.models import RegisteredUser
from office_food_bot.services import BotServices


async def register_requests_list_command(message: Message, services: BotServices) -> None:
    profile = telegram_profile_from_message(message)
    if profile is None:
        await message.answer("Не вижу твой Telegram user id.")
        return

    if not services.registration.can_approve(profile.telegram_user_id):
        await message.answer("Не могу: список заявок доступен только админам.")
        return

    pending_users = services.registration.list_pending_requests(profile.telegram_user_id)
    if not pending_users:
        await message.answer("Заявок на регистрацию нет.")
        return

    await message.answer(_pending_requests_text(pending_users))


def _pending_requests_text(pending_users: tuple[RegisteredUser, ...]) -> str:
    lines = ["Заявки на регистрацию:"]
    for index, user in enumerate(pending_users, start=1):
        username = _telegram_username_text(user)
        lines.append(
            f"{index}. {user.display_name}{username} - "
            f"Telegram ID {user.telegram_user_id} - "
            f"/approve {user.telegram_user_id}"
        )
    return "\n".join(lines)


def _telegram_username_text(user: RegisteredUser) -> str:
    if user.username is None:
        return ""
    return f" (@{user.username})"
