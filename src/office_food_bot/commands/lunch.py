from __future__ import annotations

from aiogram import Bot
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
from office_food_bot.commands.definitions import (
    CommandArgumentPattern,
    CommandDefinition,
    CommandHelpEntry,
    CommandScope,
    CommandScopeOverride,
    HelpSection,
)
from office_food_bot.execution import CommandExecutionMode
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices
from office_food_bot.services.lunch_polls import parse_lunch_office_selection

GROUP_CHAT_TYPES = frozenset({"group", "supergroup"})
GROUP_ONLY_MESSAGE = "Команда доступна только в групповом чате."
INVALID_LUNCH_OFFICE_MESSAGE = (
    "Не понял офис. Используй /lunch, /lunch rose, /lunch роза, "
    "/lunch skyline или /lunch скайлайн."
)


async def lunch_command(
    message: Message,
    command: CommandObject,
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

    argument = (command.args or "").strip().casefold()
    if argument in {"on", "off"}:
        await messenger.reply(
            message,
            services.invitations.set_lunch(
                profile.telegram_user_id,
                enabled=argument == "on",
            ),
        )
        return

    if not argument and not services.command_access.can_run_group_command_in_chat(
        str(message.chat.type),
        profile.telegram_user_id,
    ):
        await messenger.reply(
            message,
            services.invitations.lunch_status_text(profile.telegram_user_id),
        )
        return

    block_reason = services.lunch.poll_block_reason(profile.telegram_user_id)
    if block_reason is not None:
        await messenger.reply(message, block_reason)
        return

    office_selection = parse_lunch_office_selection(command.args)
    if office_selection is None:
        await messenger.reply(message, INVALID_LUNCH_OFFICE_MESSAGE)
        return

    await services.lunch_publisher.publish(
        bot,
        message.chat.id,
        mode=CommandExecutionMode.MANUAL,
        office_selection=office_selection,
    )


async def lunch_auto_on_command(
    message: Message,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    await state.clear()
    if not _is_group_chat(message):
        await messenger.reply(message, GROUP_ONLY_MESSAGE)
        return

    services.lunch_auto_chats.enable(message.chat.id, message.chat.title)
    await messenger.reply(message, "Авто-ланч включен для этого чата.")


async def lunch_auto_off_command(
    message: Message,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    await state.clear()
    if not _is_group_chat(message):
        await messenger.reply(message, GROUP_ONLY_MESSAGE)
        return

    services.lunch_auto_chats.disable(message.chat.id)
    await messenger.reply(message, "Авто-ланч выключен для этого чата.")


async def lunch_auto_status_command(
    message: Message,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    await state.clear()
    if not _is_group_chat(message):
        await messenger.reply(message, GROUP_ONLY_MESSAGE)
        return

    await messenger.reply(message, services.lunch_auto_chats.status_text(message.chat.id))


def _is_group_chat(message: Message) -> bool:
    return str(message.chat.type) in GROUP_CHAT_TYPES


class LunchCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "lunch",
        "создать опрос про обед",
        "/lunch [rose|роза|skyline|скайлайн]",
        CommandScope.GROUP,
        HelpSection.MAIN,
        additional_help=(
            CommandHelpEntry(
                "/lunch",
                "показать настройки приглашений на ланч",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.PRIVATE,
            ),
            CommandHelpEntry(
                "/lunch on",
                "включить приглашения",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.ANY,
            ),
            CommandHelpEntry(
                "/lunch off",
                "выключить приглашения",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.ANY,
            ),
        ),
        scope_overrides=(
            CommandScopeOverride(CommandArgumentPattern.EMPTY, CommandScope.ANY),
            CommandScopeOverride(CommandArgumentPattern.TOGGLE, CommandScope.ANY),
        ),
        private_description="настроить приглашения на ланч",
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
        await lunch_command(
            context.message,
            command,
            context.bot,
            context.messenger,
            self._services,
            context.state,
        )


class LunchAutoOnCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "lunch_auto_on",
        "включить авто-ланч в этом чате",
        "/lunch_auto_on",
        CommandScope.GROUP,
        HelpSection.AUTOMATION,
        admin_only=True,
    )

    def __init__(self, services: BotServices) -> None:
        super().__init__(RawArgumentsParser(), (), ())
        self._services = services

    async def execute_effect(
        self,
        context: CommandContext,
        request: RawArguments,
    ) -> None:
        await lunch_auto_on_command(
            context.message,
            context.messenger,
            self._services,
            context.state,
        )


class LunchAutoOffCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "lunch_auto_off",
        "выключить авто-ланч в этом чате",
        "/lunch_auto_off",
        CommandScope.GROUP,
        HelpSection.AUTOMATION,
        admin_only=True,
    )

    def __init__(self, services: BotServices) -> None:
        super().__init__(RawArgumentsParser(), (), ())
        self._services = services

    async def execute_effect(
        self,
        context: CommandContext,
        request: RawArguments,
    ) -> None:
        await lunch_auto_off_command(
            context.message,
            context.messenger,
            self._services,
            context.state,
        )


class LunchAutoStatusCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "lunch_auto_status",
        "показать статус авто-ланча",
        "/lunch_auto_status",
        CommandScope.GROUP,
        HelpSection.AUTOMATION,
        admin_only=True,
    )

    def __init__(self, services: BotServices) -> None:
        super().__init__(RawArgumentsParser(), (), ())
        self._services = services

    async def execute_effect(
        self,
        context: CommandContext,
        request: RawArguments,
    ) -> None:
        await lunch_auto_status_command(
            context.message,
            context.messenger,
            self._services,
            context.state,
        )
