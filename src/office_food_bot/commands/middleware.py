from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject

from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices, CommandAccessStatus

PRIVATE_ONLY_MESSAGE = "Команда доступна только в личке: https://t.me/{bot_username}"
GROUP_ONLY_MESSAGE = "Команда доступна только в групповом чате."
ADMIN_ONLY_MESSAGE = "Команда доступна только админам."


@dataclass(frozen=True)
class ParsedCommand:
    name: str
    target_bot_username: str | None


class CommandAccessMiddleware:
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, object]], Awaitable[object]],
        event: TelegramObject,
        data: dict[str, object],
    ) -> object:
        if not isinstance(event, Message):
            return await handler(event, data)

        services = data.get("services")
        if not isinstance(services, BotServices):
            return await handler(event, data)

        parsed_command = _parse_command(event.text)
        if parsed_command is None:
            return await handler(event, data)

        if _is_for_another_bot(parsed_command, services.telegram_bot_username):
            return None

        profile = telegram_profile_from_message(event)
        telegram_user_id = None
        if profile is not None:
            telegram_user_id = profile.telegram_user_id

        access = services.command_access.can_run(
            parsed_command.name,
            str(event.chat.type),
            telegram_user_id,
        )
        if access.allowed:
            return await handler(event, data)

        await _clear_state(data)
        await _reply_with_denial(event, data, access.status, services.telegram_bot_username)
        return None


def _parse_command(text: str | None) -> ParsedCommand | None:
    if text is None or not text.startswith("/"):
        return None

    command_token = text.split(maxsplit=1)[0]
    command_reference = command_token.removeprefix("/")
    if not command_reference:
        return None

    command_parts = command_reference.split("@", maxsplit=1)
    command_name = command_parts[0].casefold()
    if not command_name:
        return None

    target_bot_username = None
    if len(command_parts) == 2:
        target_bot_username = command_parts[1]

    return ParsedCommand(command_name, target_bot_username)


def _is_for_another_bot(
    parsed_command: ParsedCommand,
    bot_username: str,
) -> bool:
    if parsed_command.target_bot_username is None:
        return False
    return parsed_command.target_bot_username.casefold() != bot_username.casefold()


async def _clear_state(data: dict[str, object]) -> None:
    state = data.get("state")
    if isinstance(state, FSMContext):
        await state.clear()


async def _reply_with_denial(
    message: Message,
    data: dict[str, object],
    status: CommandAccessStatus,
    bot_username: str,
) -> None:
    text = command_access_denial_text(status, bot_username)
    messenger = data.get("messenger")
    if isinstance(messenger, BotMessenger):
        await messenger.reply(message, text)
        return

    await message.answer(text)


def command_access_denial_text(
    status: CommandAccessStatus,
    bot_username: str,
) -> str:
    if status == CommandAccessStatus.PRIVATE_ONLY:
        return PRIVATE_ONLY_MESSAGE.format(bot_username=bot_username)
    if status == CommandAccessStatus.GROUP_ONLY:
        return GROUP_ONLY_MESSAGE
    if status == CommandAccessStatus.ADMIN_ONLY:
        return ADMIN_ONLY_MESSAGE

    msg = f"Cannot build denial text for command access status {status.value}"
    raise RuntimeError(msg)
