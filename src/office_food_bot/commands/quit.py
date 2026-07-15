from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    RawArguments,
    RawArgumentsParser,
)
from office_food_bot.commanding.definition import CommandDefinition, CommandScope, HelpSection
from office_food_bot.services import BotServices

QUIT_SUCCESS_TEXT = "Вы отрегистрированы. Если захотите вернуться, отправьте /request_register."
QUIT_NOT_FOUND_TEXT = "Я не нашел вашу регистрацию."


class QuitCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "quit",
        "отрегистрироваться",
        "/quit",
        CommandScope.PRIVATE,
        HelpSection.PROFILE_SETTINGS,
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

        if self._services.registration.quit_registration(profile.telegram_user_id):
            await context.messenger.reply(
                context.message,
                QUIT_SUCCESS_TEXT,
                reply_markup=context.messenger.remove_keyboard(),
            )
            return

        await context.messenger.reply(
            context.message,
            QUIT_NOT_FOUND_TEXT,
            reply_markup=context.messenger.remove_keyboard(),
        )
