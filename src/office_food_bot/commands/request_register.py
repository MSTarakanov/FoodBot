from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    IdentityResolver,
    NoArguments,
    NoArgumentsParser,
)
from office_food_bot.commanding.definition import CommandDefinition, CommandScope, HelpSection
from office_food_bot.commanding.errors.models import CommonErrorCode, RegistrationErrorCode
from office_food_bot.commanding.errors.rendering import ErrorRenderer
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


class RequestRegisterCommand(EffectCommand[NoArguments, NoArguments]):
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
        common_error_renderer: ErrorRenderer[CommonErrorCode],
        registration: RegistrationService,
        error_renderer: ErrorRenderer[RegistrationErrorCode],
    ) -> None:
        super().__init__(
            messenger,
            common_error_renderer,
            NoArgumentsParser(),
            (TelegramIdentityValidator(),),
            (),
            IdentityResolver(),
        )
        self._registration = registration
        self._error_renderer = error_renderer

    async def execute_effect(
        self,
        context: CommandContext,
        _request: NoArguments,
    ) -> None:
        profile = require_telegram_profile(context)

        await self._registration.registration_request_eligibility(
            profile.telegram_user_id
        ).fold(
            lambda _: self._request_registration(context, profile),
            lambda code: self._reply_registration_error(context, code),
        )

    async def _request_registration(
        self,
        context: CommandContext,
        profile: TelegramProfile,
    ) -> None:
        self._registration.request_registration(profile)

        await self._messenger.reply(context.message, REQUEST_REGISTER_REPLY_TEXT)
        for admin_id in self._registration.admin_ids:
            await self._messenger.try_send(
                context.bot,
                admin_id,
                _registration_request_admin_text(profile),
            )

    async def _reply_registration_error(
        self,
        context: CommandContext,
        code: RegistrationErrorCode,
    ) -> None:
        await self._messenger.reply(
            context.message,
            self._error_renderer.render(code),
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
