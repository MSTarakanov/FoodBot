from __future__ import annotations

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commanding.access import CommandAccessService
from office_food_bot.commanding.catalog import CommandCatalog
from office_food_bot.commanding.contracts import CommandContext
from office_food_bot.commanding.definition import CommandFlowPolicy
from office_food_bot.commanding.invocation import is_for_another_bot, parse_command
from office_food_bot.commanding.profile import telegram_profile_from_message
from office_food_bot.flows.runner import FlowRunner


class CommandDispatcher:
    def __init__(
        self,
        catalog: CommandCatalog,
        access: CommandAccessService,
        bot_username: str,
        flow_runner: FlowRunner,
    ) -> None:
        self._catalog = catalog
        self._access = access
        self._bot_username = bot_username
        self._flow_runner = flow_runner

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
            await self._flow_runner.abort(message, bot, state)

        profile = telegram_profile_from_message(message)
        telegram_user_id = None if profile is None else profile.telegram_user_id
        self._access.validate_run(
            command.definition,
            str(message.chat.type),
            telegram_user_id,
        )
        await command.handle(
            CommandContext(
                message=message,
                bot=bot,
                state=state,
                profile=profile,
                invocation=invocation,
            )
        )
