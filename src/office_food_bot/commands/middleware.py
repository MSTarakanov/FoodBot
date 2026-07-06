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
        if access.allowed:
            return await handler(event, data)

        await _clear_state(data)
        await _reply_with_denial(
            event,
            self._messenger,
            access.status,
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
    status: CommandAccessStatus,
    bot_username: str,
) -> None:
    text = command_access_denial_text(status, bot_username)
    await messenger.reply(message, text)


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
