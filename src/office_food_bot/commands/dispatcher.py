from __future__ import annotations

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commands.base import CommandContext
from office_food_bot.commands.catalog import CommandCatalog
from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.commands.definitions import CommandFlowPolicy
from office_food_bot.commands.parsing import is_for_another_bot, parse_command
from office_food_bot.messaging import BotMessenger
from office_food_bot.services.command_access import CommandAccessService


class CommandDispatcher:
    def __init__(
        self,
        catalog: CommandCatalog,
        access: CommandAccessService,
        messenger: BotMessenger,
        bot_username: str,
    ) -> None:
        self._catalog = catalog
        self._access = access
        self._messenger = messenger
        self._bot_username = bot_username

    async def dispatch(
        self,
        message: Message,
        bot: Bot,
        state: FSMContext,
    ) -> None:
        invocation = parse_command(message.text)
        if invocation is None:
            return
        if is_for_another_bot(invocation, self._bot_username):
            return

        command = self._catalog.resolve(invocation.name)
        if command is None:
            return
        if command.definition.flow_policy == CommandFlowPolicy.RESET_BEFORE_RUN:
            await state.clear()

        profile = telegram_profile_from_message(message)
        telegram_user_id = None if profile is None else profile.telegram_user_id
        self._access.validate_run(
            command.definition,
            str(message.chat.type),
            telegram_user_id,
            invocation.arguments,
        )
        await command.handle(
            CommandContext(
                message=message,
                bot=bot,
                messenger=self._messenger,
                state=state,
                profile=profile,
                invocation=invocation,
                catalog=self._catalog,
            )
        )
