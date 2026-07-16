from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    NoArguments,
    NoArgumentsParser,
)
from office_food_bot.commanding.definition import CommandDefinition, CommandScope, HelpSection
from office_food_bot.commanding.errors.models import CommonErrorCode
from office_food_bot.commanding.errors.rendering import ErrorRenderer
from office_food_bot.commanding.validators import (
    TelegramIdentityValidator,
    require_telegram_profile,
)
from office_food_bot.messaging import BotMessenger
from office_food_bot.models import (
    KnownTelegramAccount,
    PendingRegistration,
    RegisteredUser,
    SplitwiseConnection,
)
from office_food_bot.services.registration import RegistrationService


class RegisterRequestsListCommand(EffectCommand[NoArguments]):
    definition = CommandDefinition(
        "register_requests_list",
        "показать заявки на регистрацию",
        "/register_requests_list",
        CommandScope.PRIVATE,
        HelpSection.ADMINISTRATION,
        admin_only=True,
    )

    def __init__(
        self,
        messenger: BotMessenger,
        common_error_renderer: ErrorRenderer[CommonErrorCode],
        registration: RegistrationService,
    ) -> None:
        super().__init__(
            messenger,
            common_error_renderer,
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
        if not self._registration.can_approve(profile.telegram_user_id):
            await self._reply_common_error(context, CommonErrorCode.ADMIN_REQUIRED)
            return

        pending_requests = self._registration.list_pending_requests(
            profile.telegram_user_id
        )
        requested_accounts = self._registration.list_requested_telegram_accounts(
            profile.telegram_user_id,
        )
        seen_accounts = self._registration.list_seen_telegram_accounts(
            profile.telegram_user_id
        )
        await self._messenger.reply(
            context.message,
            _registration_requests_text(
                pending_requests,
                requested_accounts,
                seen_accounts,
            ),
        )


def _registration_requests_text(
    pending_requests: tuple[PendingRegistration, ...],
    requested_accounts: tuple[KnownTelegramAccount, ...],
    seen_accounts: tuple[KnownTelegramAccount, ...],
) -> str:
    lines: list[str] = []
    if pending_requests:
        lines.append(_pending_requests_text(pending_requests))
    elif not requested_accounts:
        lines.append("Заявок на регистрацию нет.")

    if requested_accounts:
        if lines:
            lines.append("")
        lines.append(
            _telegram_accounts_registration_text(
                "Попросили регистрацию:",
                requested_accounts,
            )
        )

    if seen_accounts:
        if lines:
            lines.append("")
        lines.append(
            _telegram_accounts_registration_text(
                "Видел незарегистрированных пользователей:",
                seen_accounts,
            )
        )

    return "\n".join(lines)


def _pending_requests_text(pending_users: tuple[PendingRegistration, ...]) -> str:
    lines = ["Заявки на регистрацию:"]
    for index, registration in enumerate(pending_users, start=1):
        user = registration.user
        username = _telegram_username_text(user)
        lines.append(
            f"{index}. {user.display_name}{username} - "
            f"Telegram ID {user.telegram_user_id} - "
            f"{_splitwise_text(registration.splitwise)} - "
            f"/approve {user.telegram_user_id}"
        )
    return "\n".join(lines)


def _telegram_username_text(user: RegisteredUser) -> str:
    if user.username is None:
        return ""
    return f" (@{user.username})"


def _splitwise_text(splitwise: SplitwiseConnection | None) -> str:
    if splitwise is None:
        return "Splitwise: не указан"
    if splitwise.email is None:
        return f"Splitwise: email не указан (ID {splitwise.splitwise_user_id})"
    return f"Splitwise: {splitwise.email} (ID {splitwise.splitwise_user_id})"


def _telegram_accounts_registration_text(
    title: str,
    telegram_accounts: tuple[KnownTelegramAccount, ...],
) -> str:
    lines = [title]
    for index, telegram_account in enumerate(telegram_accounts, start=1):
        lines.append(
            f"{index}. {_telegram_account_display_text(telegram_account)} - "
            f"Telegram ID {telegram_account.telegram_user_id} - "
            f"/register {telegram_account.telegram_user_id}"
        )
    return "\n".join(lines)


def _telegram_account_display_text(telegram_account: KnownTelegramAccount) -> str:
    display_name = " ".join(
        part
        for part in (telegram_account.first_name, telegram_account.last_name)
        if part is not None
    )
    if not display_name:
        display_name = f"Telegram ID {telegram_account.telegram_user_id}"
    if telegram_account.username is None:
        return display_name
    return f"{display_name} (@{telegram_account.username})"
