from __future__ import annotations

from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    RawArguments,
    RawArgumentsParser,
)
from office_food_bot.commanding.definition import (
    CommandDefinition,
    CommandHelpEntry,
    CommandScope,
    HelpSection,
)
from office_food_bot.commanding.profile import telegram_profile_from_message
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices


async def vacation_command(
    message: Message,
    command: CommandObject,
    messenger: BotMessenger,
    services: BotServices,
    state: FSMContext,
) -> None:
    await state.clear()
    profile = telegram_profile_from_message(message)
    if profile is None:
        await messenger.reply(message, "Не вижу твой Telegram user id.")
        return

    await messenger.reply(
        message,
        services.vacation.reply(profile.telegram_user_id, command.args or ""),
    )


class VacationCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "vacation",
        "показать статус отпуска",
        "/vacation",
        CommandScope.GROUP,
        HelpSection.PROFILE_SETTINGS,
        additional_help=(
            CommandHelpEntry(
                "/vacation 2 или /vacation 20.07",
                "уйти в отпуск",
                HelpSection.PROFILE_SETTINGS,
            ),
            CommandHelpEntry(
                "/vacation 0 или /vacation off",
                "выйти из отпуска",
                HelpSection.PROFILE_SETTINGS,
            ),
        ),
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
        await vacation_command(
            context.message,
            command,
            context.messenger,
            self._services,
            context.state,
        )
