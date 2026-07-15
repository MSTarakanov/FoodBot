from __future__ import annotations

from aiogram.filters.command import CommandObject
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


async def eta_command(
    message: Message,
    command: CommandObject,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    command_name = command.command
    await state.clear()
    profile = telegram_profile_from_message(message)
    if profile is None:
        await messenger.reply(message, "Не вижу твой Telegram user id.")
        return

    if not command.args:
        await messenger.reply(
            message,
            services.presence.eta_missing_minutes_reply(command_name),
        )
        return

    await messenger.reply(
        message,
        services.presence.eta(profile.telegram_user_id, command.args, command_name),
    )


class EtaCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "eta",
        "сообщить ожидаемое время доставки",
        "/eta 20 или /eta 20-30",
        CommandScope.GROUP,
        HelpSection.MAIN,
    )

    def __init__(self, services: BotServices) -> None:
        super().__init__(RawArgumentsParser(), (), ())
        self._services = services

    async def execute_effect(
        self,
        context: CommandContext,
        request: RawArguments,
    ) -> None:
        await _execute_eta_command(context, request, self._services)


class MetaCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "meta",
        "сообщить, через сколько минут или в каком диапазоне придешь",
        "/meta 25 или /meta 20-30",
        CommandScope.GROUP,
        HelpSection.MAIN,
    )

    def __init__(self, services: BotServices) -> None:
        super().__init__(RawArgumentsParser(), (), ())
        self._services = services

    async def execute_effect(
        self,
        context: CommandContext,
        request: RawArguments,
    ) -> None:
        await _execute_eta_command(context, request, self._services)


async def _execute_eta_command(
    context: CommandContext,
    request: RawArguments,
    services: BotServices,
) -> None:
    command = CommandObject(command=context.invocation.name, args=request.value)
    await eta_command(
        context.message,
        command,
        context.messenger,
        services,
        context.state,
    )
