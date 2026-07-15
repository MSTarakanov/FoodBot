from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    RawArguments,
    RawArgumentsParser,
)
from office_food_bot.commanding.definition import CommandDefinition, CommandScope, HelpSection
from office_food_bot.models import TelegramProfile
from office_food_bot.services import BotServices

REQUEST_REGISTER_REPLY_TEXT = (
    "Запрос на регистрацию отправлен админам. "
    "Теперь администратор сможет зарегистрировать тебя."
)


class RequestRegisterCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "request_register",
        "попросить админа зарегистрировать вас",
        "/request_register",
        CommandScope.ANY,
        HelpSection.PROFILE_SETTINGS,
        show_in_menu=False,
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

        block_reason = self._services.registration.request_registration_block_reason(
            profile.telegram_user_id,
        )
        if block_reason is not None:
            await context.messenger.reply(context.message, block_reason)
            return

        self._services.registration.request_registration(profile)

        await context.messenger.reply(context.message, REQUEST_REGISTER_REPLY_TEXT)
        for admin_id in self._services.registration.admin_ids:
            await context.messenger.try_send(
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
