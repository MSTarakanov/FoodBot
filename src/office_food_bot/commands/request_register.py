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
from office_food_bot.models import TelegramProfile
from office_food_bot.services.registration import RegistrationService

REQUEST_REGISTER_REPLY_TEXT = (
    "Запрос на регистрацию отправлен админам. "
    "Теперь администратор сможет зарегистрировать тебя."
)


class RequestRegisterCommand(EffectCommand[NoArguments]):
    definition = CommandDefinition(
        "request_register",
        "попросить админа зарегистрировать вас",
        "/request_register",
        CommandScope.ANY,
        HelpSection.PROFILE_SETTINGS,
        show_in_menu=False,
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

        self._registration.ensure_registration_can_be_requested(
            profile.telegram_user_id,
        )
        self._registration.request_registration(profile)

        await self._messenger.reply(context.message, REQUEST_REGISTER_REPLY_TEXT)
        for admin_id in self._registration.admin_ids:
            await self._messenger.try_send(
                context.bot,
                admin_id,
                _registration_request_admin_text(profile),
            )


def _registration_request_admin_text(profile: TelegramProfile) -> str:
    return (
        "Запрос на регистрацию:\n"
        f"Telegram ID: {profile.telegram_user_id}\n"
        f"Username: {_profile_username_text(profile)}\n"
        f"Имя в Telegram: {_profile_display_name_text(profile)}\n"
        f"Начать регистрацию: /register {profile.telegram_user_id}"
    )


def _profile_username_text(profile: TelegramProfile) -> str:
    if profile.username is None:
        return "не указан"
    return f"@{profile.username}"


def _profile_display_name_text(profile: TelegramProfile) -> str:
    return " ".join(
        part
        for part in (profile.first_name, profile.last_name)
        if part is not None
    )
