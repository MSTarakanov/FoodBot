from __future__ import annotations

from typing import assert_never

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commanding.access import CommandAccessService
from office_food_bot.commanding.catalog import CommandCatalog
from office_food_bot.commanding.contracts import CommandContext
from office_food_bot.commanding.definition import CommandFlowPolicy
from office_food_bot.commanding.errors.models import CommonErrorCode
from office_food_bot.commanding.errors.rendering import ErrorRenderer
from office_food_bot.commanding.invocation import is_for_another_bot, parse_command
from office_food_bot.commanding.profile import telegram_profile_from_message
from office_food_bot.flows.runner import FlowRunner
from office_food_bot.messaging import BotMessenger


class CommandDispatcher:
    def __init__(
        self,
        catalog: CommandCatalog,
        access: CommandAccessService,
        bot_username: str,
        flow_runner: FlowRunner,
        messenger: BotMessenger,
        common_error_renderer: ErrorRenderer[CommonErrorCode],
    ) -> None:
        self._catalog = catalog
        self._access = access
        self._bot_username = bot_username
        self._flow_runner = flow_runner
        self._messenger = messenger
        self._common_error_renderer = common_error_renderer

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
        match command.definition.flow_policy:
            case CommandFlowPolicy.RESET_BEFORE_RUN:
                await self._flow_runner.abort(message, bot, state)
            case CommandFlowPolicy.MANAGED_BY_COMMAND:
                pass
            case _:
                assert_never(command.definition.flow_policy)

        profile = telegram_profile_from_message(message)
        telegram_user_id = None if profile is None else profile.telegram_user_id
        authorization = self._access.authorize_run(
            command.definition,
            str(message.chat.type),
            telegram_user_id,
        )
        context = CommandContext(
            message=message,
            bot=bot,
            state=state,
            profile=profile,
            invocation=invocation,
        )
        await authorization.fold(
            lambda _: command.handle(context),
            lambda code: self._reply_access_error(message, code),
        )

    async def _reply_access_error(
        self,
        message: Message,
        code: CommonErrorCode,
    ) -> None:
        await self._messenger.reply(
            message,
            self._common_error_renderer.render(code),
        )
