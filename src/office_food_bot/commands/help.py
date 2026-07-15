from __future__ import annotations

from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commands.base import (
    CommandContext,
    EffectCommand,
    RawArguments,
    RawArgumentsParser,
)
from office_food_bot.commands.catalog import CommandCatalog
from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.commands.definitions import CommandDefinition, CommandScope, HelpSection
from office_food_bot.commands.help_renderer import HELP_RENDERER
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices


async def help_command(
    message: Message,
    messenger: BotMessenger,
    services: BotServices,
    catalog: CommandCatalog,
    state: FSMContext,
) -> None:
    await state.clear()
    profile = telegram_profile_from_message(message)
    telegram_user_id = None
    if profile is not None:
        telegram_user_id = profile.telegram_user_id

    await messenger.reply(
        message,
        HELP_RENDERER.render(
            services.command_access.visible_help_entries(
                catalog.definitions,
                str(message.chat.type),
                telegram_user_id,
            )
        ),
        parse_mode=ParseMode.HTML,
    )


class HelpCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "help",
        "показать список команд",
        "/help",
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
        await help_command(
            context.message,
            context.messenger,
            self._services,
            context.catalog,
            context.state,
        )
