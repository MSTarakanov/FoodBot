from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject

from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices, CommandAccessDenialReason

PRIVATE_ONLY_MESSAGE = "Команда доступна только в личке: https://t.me/{bot_username}"
GROUP_ONLY_MESSAGE = "Команда доступна только в групповом чате."
ADMIN_ONLY_MESSAGE = "Команда доступна только админам."
DENIAL_MESSAGE_TEMPLATES = {
    CommandAccessDenialReason.PRIVATE_ONLY: PRIVATE_ONLY_MESSAGE,
    CommandAccessDenialReason.GROUP_ONLY: GROUP_ONLY_MESSAGE,
    CommandAccessDenialReason.ADMIN_ONLY: ADMIN_ONLY_MESSAGE,
}


@dataclass(frozen=True)
class ParsedCommand:
    name: str
    target_bot_username: str | None


CommandMiddlewareData = dict[str, FSMContext]


CommandHandler = Callable[
    [TelegramObject, CommandMiddlewareData],
    Awaitable[TelegramObject | None],
]


class CommandAccessMiddleware:
    def __init__(self, services: BotServices, messenger: BotMessenger) -> None:
        self._services = services
        self._messenger = messenger

    async def __call__(
        self,
        handler: CommandHandler,
        event: TelegramObject,
        data: CommandMiddlewareData,
    ) -> TelegramObject | None:
        if not isinstance(event, Message):
            return await handler(event, data)

        parsed_command = _parse_command(event.text)
        if parsed_command is None:
            return await handler(event, data)

        if _is_for_another_bot(parsed_command, self._services.telegram_bot_username):
            return None

        profile = telegram_profile_from_message(event)
        telegram_user_id = None
        if profile is not None:
            telegram_user_id = profile.telegram_user_id

        access = self._services.command_access.can_run(
            parsed_command.name,
            str(event.chat.type),
            telegram_user_id,
        )
        denial_reason = access.denial_reason
        if denial_reason is None:
            return await handler(event, data)

        await _clear_state(data)
        await _reply_with_denial(
            event,
            self._messenger,
            denial_reason,
            self._services.telegram_bot_username,
        )
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


async def _clear_state(data: CommandMiddlewareData) -> None:
    state = data.get("state")
    if state is not None:
        await state.clear()


async def _reply_with_denial(
    message: Message,
    messenger: BotMessenger,
    reason: CommandAccessDenialReason,
    bot_username: str,
) -> None:
    text = command_access_denial_text(reason, bot_username)
    await messenger.reply(message, text)


def command_access_denial_text(
    reason: CommandAccessDenialReason,
    bot_username: str,
) -> str:
    return DENIAL_MESSAGE_TEMPLATES[reason].format(bot_username=bot_username)
