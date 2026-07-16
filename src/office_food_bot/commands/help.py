from __future__ import annotations

from aiogram.enums import ParseMode

from office_food_bot.commanding.access import CommandAccessService
from office_food_bot.commanding.catalog import CommandCatalogProvider
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
from office_food_bot.commanding.help import HELP_RENDERER
from office_food_bot.messaging import BotMessenger


class HelpCommand(EffectCommand[NoArguments, NoArguments]):
    definition = CommandDefinition(
        "help",
        "показать список команд",
        "/help",
        CommandScope.ANY,
        HelpSection.SERVICE,
    )

    def __init__(
        self,
        messenger: BotMessenger,
        common_error_renderer: ErrorRenderer[CommonErrorCode],
        access: CommandAccessService,
        catalog: CommandCatalogProvider,
    ) -> None:
        super().__init__(
            messenger,
            common_error_renderer,
            NoArgumentsParser(),
            (),
            (),
            IdentityResolver(),
        )
        self._access = access
        self._catalog = catalog

    async def execute_effect(
        self,
        context: CommandContext,
        _request: NoArguments,
    ) -> None:
        telegram_user_id = None
        if context.profile is not None:
            telegram_user_id = context.profile.telegram_user_id
        await self._messenger.reply(
            context.message,
            HELP_RENDERER.render(
                self._access.visible_help_entries(
                    self._catalog().definitions,
                    str(context.message.chat.type),
                    telegram_user_id,
                )
            ),
            parse_mode=ParseMode.HTML,
        )
