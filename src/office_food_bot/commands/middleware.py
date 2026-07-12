from __future__ import annotations

from collections.abc import Awaitable, Callable

from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject

from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.commands.definitions import command_definition
from office_food_bot.commands.parsing import is_for_another_bot, parse_command
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

        parsed_command = parse_command(event.text)
        if parsed_command is None:
            return await handler(event, data)

        if is_for_another_bot(parsed_command, self._services.telegram_bot_username):
            return None

        profile = telegram_profile_from_message(event)
        telegram_user_id = None
        if profile is not None:
            telegram_user_id = profile.telegram_user_id

        definition = command_definition(parsed_command.name)
        command_name = parsed_command.name
        if definition is not None:
            command_name = definition.name

        access = self._services.command_access.can_run(
            command_name,
            str(event.chat.type),
            telegram_user_id,
            parsed_command.arguments,
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
