from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    NoArguments,
    NoArgumentsParser,
)
from office_food_bot.commanding.definition import CommandDefinition, CommandScope, HelpSection
from office_food_bot.commanding.validators import (
    TelegramIdentityValidator,
    require_telegram_profile,
)
from office_food_bot.messaging import BotMessenger
from office_food_bot.services.registration import RegistrationService

QUIT_SUCCESS_TEXT = "Вы отрегистрированы. Если захотите вернуться, отправьте /request_register."
QUIT_NOT_FOUND_TEXT = "Я не нашел вашу регистрацию."


class QuitCommand(EffectCommand[NoArguments]):
    definition = CommandDefinition(
        "quit",
        "отрегистрироваться",
        "/quit",
        CommandScope.PRIVATE,
        HelpSection.PROFILE_SETTINGS,
    )

    def __init__(
        self,
        messenger: BotMessenger,
        registration: RegistrationService,
    ) -> None:
        super().__init__(
            messenger,
            NoArgumentsParser(),
            (TelegramIdentityValidator(),),
            (),
        )
        self._registration = registration

    async def execute_effect(
        self,
        context: CommandContext,
        request: NoArguments,
    ) -> None:
        del request
        profile = require_telegram_profile(context)

        if self._registration.quit_registration(profile.telegram_user_id):
            await self._messenger.reply(
                context.message,
                QUIT_SUCCESS_TEXT,
                reply_markup=self._messenger.remove_keyboard(),
            )
            return

        await self._messenger.reply(
            context.message,
            QUIT_NOT_FOUND_TEXT,
            reply_markup=self._messenger.remove_keyboard(),
        )
