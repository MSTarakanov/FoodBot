from __future__ import annotations

import logging

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commands.base import (
    CommandContext,
    EffectCommand,
    RawArguments,
    RawArgumentsParser,
)
from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.commands.definitions import CommandDefinition, CommandScope, HelpSection
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices

logger = logging.getLogger(__name__)


async def hi_command(
    message: Message,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    await state.clear()
    profile = telegram_profile_from_message(message)
    if profile is not None:
        services.telegram_interactions.remember(profile)
    logger.warning(
        "/hi handled by @%s: chat_id=%s, telegram_user_id=%s",
        services.telegram_bot_username,
        message.chat.id,
        message.from_user.id if message.from_user is not None else None,
    )
    await messenger.reply(message, "Привет! Я на месте.")


class HiCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "hi",
        "проверить, что бот на месте",
        "/hi",
        CommandScope.ANY,
        HelpSection.SERVICE,
    )

    def __init__(self, services: BotServices) -> None:
        super().__init__(RawArgumentsParser(), (), ())
        self._services = services

    async def execute_effect(
        self,
        context: CommandContext,
        request: RawArguments,
    ) -> None:
        await hi_command(
            context.message,
            context.messenger,
            self._services,
            context.state,
        )
