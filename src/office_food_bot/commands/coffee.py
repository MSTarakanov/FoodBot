from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from office_food_bot.coffee_models import CoffeeTimeResolutionKind
from office_food_bot.commanding.access import CommandAccessService
from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
)
from office_food_bot.commanding.definition import (
    CommandDefinition,
    CommandHelpEntry,
    CommandInputMessage,
    CommandScope,
    HelpSection,
)
from office_food_bot.commanding.errors.models import (
    CommonErrorCode,
    InputErrorCode,
)
from office_food_bot.commanding.errors.rendering import ErrorRenderer
from office_food_bot.commanding.validators import (
    ActiveUserValidator,
    TelegramIdentityValidator,
    require_telegram_profile,
)
from office_food_bot.invitation_models import InvitationKind
from office_food_bot.messaging import BotMessenger
from office_food_bot.presenters.coffee import CoffeeCommandRenderer
from office_food_bot.presenters.invitations import render_invitation_setting
from office_food_bot.result import Result, failure, success
from office_food_bot.services.coffee import CoffeeService, CoffeeTimeResolver
from office_food_bot.services.invitations import InvitationPreferenceService
from office_food_bot.services.user_access import ActiveUserResolver

COFFEE_TIME_ERROR = (
    "Не понял время. Напиши минуты или время сегодня: /coffee 15 или /coffee 16:30."
)
COFFEE_TIME_RANGE_ERROR = "Время кофе должно быть минимум через минуту и до конца сегодня."


@dataclass(frozen=True, slots=True)
class CoffeeRequest:
    pass


@dataclass(frozen=True, slots=True)
class CoffeeStatusRequest(CoffeeRequest):
    pass


@dataclass(frozen=True, slots=True)
class CoffeeToggleRequest(CoffeeRequest):
    enabled: bool


@dataclass(frozen=True, slots=True)
class CoffeeScheduleRequest(CoffeeRequest):
    scheduled_at: datetime


class CoffeeRequestParser:
    def __init__(self, coffee_time: CoffeeTimeResolver) -> None:
        self._coffee_time = coffee_time

    def parse(
        self,
        raw_arguments: str | None,
    ) -> Result[CoffeeRequest, InputErrorCode]:
        argument = (raw_arguments or "").strip()
        if not argument:
            return success(CoffeeStatusRequest())
        normalized = argument.casefold()
        if normalized in {"on", "off"}:
            return success(CoffeeToggleRequest(normalized == "on"))
        resolution = self._coffee_time.resolve(argument)
        if resolution.kind == CoffeeTimeResolutionKind.INVALID_FORMAT:
            return failure(InputErrorCode.INVALID_FORMAT)
        if resolution.kind == CoffeeTimeResolutionKind.OUT_OF_RANGE:
            return failure(InputErrorCode.OUT_OF_RANGE)
        if resolution.scheduled_at is None:
            raise RuntimeError("Valid coffee schedule has no timestamp")
        return success(CoffeeScheduleRequest(resolution.scheduled_at))


class CoffeeScheduleScopeValidator:
    def __init__(self, access: CommandAccessService) -> None:
        self._access = access

    def validate(
        self,
        context: CommandContext,
        request: CoffeeRequest,
    ) -> Result[None, CommonErrorCode]:
        match request:
            case CoffeeStatusRequest() | CoffeeToggleRequest():
                return success(None)
            case CoffeeScheduleRequest():
                profile = require_telegram_profile(context)
                if not self._access.can_run_group_command_in_chat(
                    str(context.message.chat.type),
                    profile.telegram_user_id,
                ):
                    return failure(CommonErrorCode.GROUP_CHAT_REQUIRED)
                return success(None)
            case _:
                raise RuntimeError(
                    f"Unsupported coffee request: {type(request).__name__}"
                )


class CoffeeCommand(EffectCommand[CoffeeRequest]):
    definition = CommandDefinition(
        "coffee",
        "позвать на кофе",
        "/coffee 15 или /coffee 16:30",
        CommandScope.ANY,
        HelpSection.MAIN,
        help_scope=CommandScope.GROUP,
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
        private_description="настроить приглашения на кофе",
        input_errors=(
            CommandInputMessage(InputErrorCode.INVALID_FORMAT, COFFEE_TIME_ERROR),
            CommandInputMessage(InputErrorCode.OUT_OF_RANGE, COFFEE_TIME_RANGE_ERROR),
        ),
    )

    def __init__(
        self,
        messenger: BotMessenger,
        common_error_renderer: ErrorRenderer[CommonErrorCode],
        coffee: CoffeeService,
        coffee_time: CoffeeTimeResolver,
        renderer: CoffeeCommandRenderer,
        invitations: InvitationPreferenceService,
        access: CommandAccessService,
        active_users: ActiveUserResolver,
    ) -> None:
        super().__init__(
            messenger,
            common_error_renderer,
            CoffeeRequestParser(coffee_time),
            (TelegramIdentityValidator(),),
            (
                CoffeeScheduleScopeValidator(access),
                ActiveUserValidator(active_users),
            ),
        )
        self._coffee = coffee
        self._renderer = renderer
        self._invitations = invitations
        self._active_users = active_users

    async def execute_effect(
        self,
        context: CommandContext,
        request: CoffeeRequest,
    ) -> None:
        profile = require_telegram_profile(context)
        match request:
            case CoffeeStatusRequest():
                user = self._active_users.require_validated(profile.telegram_user_id)
                await self._messenger.reply(
                    context.message,
                    self._renderer.status(
                        self._coffee.status(
                            user,
                            context.message.chat.id,
                        )
                    ),
                )
            case CoffeeToggleRequest():
                await self._messenger.reply(
                    context.message,
                    render_invitation_setting(
                        self._invitations.set_enabled(
                            profile.telegram_user_id,
                            InvitationKind.COFFEE,
                            request.enabled,
                        )
                    ),
                )
            case CoffeeScheduleRequest():
                user = self._active_users.require_validated(profile.telegram_user_id)
                await self._coffee.create_or_reschedule(
                    context.bot,
                    context.message.chat.id,
                    user,
                    request.scheduled_at,
                )
            case _:
                raise RuntimeError(
                    f"Unsupported coffee request: {type(request).__name__}"
                )
