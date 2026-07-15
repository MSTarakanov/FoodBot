from __future__ import annotations

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
from office_food_bot.services import BotServices


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
        profile = context.profile
        if profile is None:
            await context.messenger.reply(
                context.message,
                "Не вижу твой Telegram user id.",
            )
            return

        await context.messenger.reply(
            context.message,
            self._services.vacation.reply(
                profile.telegram_user_id,
                request.value or "",
            ),
        )
