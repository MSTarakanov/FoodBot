from __future__ import annotations

import logging

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    IdentityResolver,
    NoArguments,
    NoArgumentsParser,
)
from office_food_bot.commanding.definition import CommandDefinition, CommandScope, HelpSection
from office_food_bot.commanding.errors.models import CommonErrorCode
from office_food_bot.commanding.errors.rendering import ErrorRenderer
from office_food_bot.infrastructure.telegram_interactions import TelegramInteractionService
from office_food_bot.messaging import BotMessenger

logger = logging.getLogger(__name__)


class HiCommand(EffectCommand[NoArguments, NoArguments]):
    definition = CommandDefinition(
        "hi",
        "проверить, что бот на месте",
        "/hi",
        CommandScope.ANY,
        HelpSection.SERVICE,
    )

    def __init__(
        self,
        messenger: BotMessenger,
        common_error_renderer: ErrorRenderer[CommonErrorCode],
        interactions: TelegramInteractionService,
        bot_username: str,
    ) -> None:
        super().__init__(
            messenger,
            common_error_renderer,
            NoArgumentsParser(),
            (),
            (),
            IdentityResolver(),
        )
        self._interactions = interactions
        self._bot_username = bot_username

    async def execute_effect(
        self,
        context: CommandContext,
        _request: NoArguments,
    ) -> None:
        if context.profile is not None:
            self._interactions.remember(context.profile)
        logger.warning(
            "/hi handled by @%s: chat_id=%s, telegram_user_id=%s",
            self._bot_username,
            context.message.chat.id,
            (
                context.message.from_user.id
                if context.message.from_user is not None
                else None
            ),
        )
        await self._messenger.reply(context.message, "Привет! Я на месте.")
