from __future__ import annotations

from aiogram import Bot
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from office_food_bot.coffee_callbacks import CoffeeCallbackData
from office_food_bot.commands.base import (
    CommandContext,
    EffectCommand,
    RawArguments,
    RawArgumentsParser,
)
from office_food_bot.commands.common import telegram_profile_from_message
from office_food_bot.commands.definitions import (
    CommandArgumentPattern,
    CommandDefinition,
    CommandHelpEntry,
    CommandScope,
    CommandScopeOverride,
    HelpSection,
)
from office_food_bot.commands.parsing import ParsedCommand
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices


async def coffee_command(
    message: Message,
    command: CommandObject,
    bot: Bot,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    await _handle_coffee_command(
        message,
        command.args,
        bot,
        messenger,
        services,
        state,
    )


async def coffee_alias_command(
    message: Message,
    alias_command: ParsedCommand,
    bot: Bot,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    await _handle_coffee_command(
        message,
        alias_command.arguments,
        bot,
        messenger,
        services,
        state,
    )


async def _handle_coffee_command(
    message: Message,
    raw_argument: str | None,
    bot: Bot,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    await state.clear()
    profile = telegram_profile_from_message(message)
    if profile is None:
        await messenger.reply(message, "Не вижу твой Telegram user id.")
        return
    argument = (raw_argument or "").strip()
    if not argument:
        await messenger.reply(
            message,
            services.coffee.status_text(profile.telegram_user_id, message.chat.id),
        )
        return
    normalized = argument.casefold()
    if normalized in {"on", "off"}:
        await messenger.reply(
            message,
            services.coffee.set_invitations(
                profile.telegram_user_id,
                enabled=normalized == "on",
            ),
        )
        return
    error = await services.coffee.create_or_reschedule(
        bot,
        message.chat.id,
        profile.telegram_user_id,
        argument,
    )
    if error is not None:
        await messenger.reply(message, error)


async def coffee_callback_handler(
    callback_query: CallbackQuery,
    bot: Bot,
    services: BotServices,
) -> None:
    callback_data = CoffeeCallbackData.unpack(callback_query.data or "")
    if callback_data is None:
        await callback_query.answer("Не понял действие.", show_alert=True)
        return
    result = await services.coffee.update_participation(
        bot,
        callback_query.from_user.id,
        callback_data,
    )
    await callback_query.answer(result.text, show_alert=result.show_alert)


class CoffeeCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "coffee",
        "позвать на кофе",
        "/coffee 15 или /coffee 16:30",
        CommandScope.GROUP,
        HelpSection.MAIN,
        additional_help=(
            CommandHelpEntry(
                "/coffee",
                "показать настройки приглашений на кофе",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.PRIVATE,
            ),
            CommandHelpEntry(
                "/coffee on",
                "включить приглашения",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.ANY,
            ),
            CommandHelpEntry(
                "/coffee off",
                "выключить приглашения",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.ANY,
            ),
        ),
        text_aliases=("кофе",),
        scope_overrides=(
            CommandScopeOverride(CommandArgumentPattern.EMPTY, CommandScope.ANY),
            CommandScopeOverride(CommandArgumentPattern.TOGGLE, CommandScope.ANY),
        ),
        private_description="настроить приглашения на кофе",
    )

    def __init__(self, services: BotServices) -> None:
        super().__init__(RawArgumentsParser(), (), ())
        self._services = services

    async def execute_effect(
        self,
        context: CommandContext,
        request: RawArguments,
    ) -> None:
        command = CommandObject(command=context.invocation.name, args=request.value)
        await coffee_command(
            context.message,
            command,
            context.bot,
            context.messenger,
            self._services,
            context.state,
        )
