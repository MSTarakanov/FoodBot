from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import assert_never

from office_food_bot.application.users.resolver import ActiveUserResolver
from office_food_bot.boolean_input import parse_toggle
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
from office_food_bot.features.coffee.models import CoffeeTimeResolutionKind
from office_food_bot.features.coffee.rendering import CoffeeCommandRenderer
from office_food_bot.features.coffee.service import CoffeeService, CoffeeTimeResolver
from office_food_bot.features.invitations.models import InvitationKind
from office_food_bot.features.invitations.rendering import render_invitation_setting
from office_food_bot.features.invitations.service import InvitationPreferenceService
from office_food_bot.messaging import BotMessenger
from office_food_bot.result import Result, failure, success

COFFEE_TIME_ERROR = (
    "Не понял время. Напиши минуты или время сегодня: /coffee 15 или /coffee 16:30."
)
COFFEE_TIME_RANGE_ERROR = "Время кофе должно быть минимум через минуту и до конца сегодня."


class CoffeeInput:
    pass


@dataclass(frozen=True, slots=True)
class CoffeeStatusInput(CoffeeInput):
    pass


@dataclass(frozen=True, slots=True)
class CoffeeToggleInput(CoffeeInput):
    enabled: bool


@dataclass(frozen=True, slots=True)
class CoffeeScheduleInput(CoffeeInput):
    raw_time: str


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
    def parse(
        self,
        raw_arguments: str | None,
    ) -> CoffeeInput:
        argument = (raw_arguments or "").strip()
        if not argument:
            return CoffeeStatusInput()
        enabled = parse_toggle(argument)
        if enabled is not None:
            return CoffeeToggleInput(enabled)
        return CoffeeScheduleInput(argument)


class CoffeeRequestResolver:
    def __init__(self, coffee_time: CoffeeTimeResolver) -> None:
        self._coffee_time = coffee_time

    def resolve(
        self,
        value: CoffeeInput,
    ) -> Result[CoffeeRequest, InputErrorCode]:
        match value:
            case CoffeeStatusInput():
                return success(CoffeeStatusRequest())
            case CoffeeToggleInput():
                return success(CoffeeToggleRequest(value.enabled))
            case CoffeeScheduleInput():
                resolution = self._coffee_time.resolve(value.raw_time)
                match resolution.kind:
                    case CoffeeTimeResolutionKind.INVALID_FORMAT:
                        return failure(InputErrorCode.INVALID_FORMAT)
                    case CoffeeTimeResolutionKind.OUT_OF_RANGE:
                        return failure(InputErrorCode.OUT_OF_RANGE)
                    case CoffeeTimeResolutionKind.VALID:
                        if resolution.scheduled_at is None:
                            raise RuntimeError(
                                "Valid coffee schedule has no timestamp"
                            )
                        return success(
                            CoffeeScheduleRequest(resolution.scheduled_at)
                        )
                assert_never(resolution.kind)
            case _:
                raise RuntimeError(f"Unsupported coffee input: {type(value).__name__}")


class CoffeeScheduleScopeValidator:
    def __init__(self, access: CommandAccessService) -> None:
        self._access = access

    def validate(
        self,
        context: CommandContext,
        request: CoffeeInput,
    ) -> Result[None, CommonErrorCode]:
        match request:
            case CoffeeStatusInput() | CoffeeToggleInput():
                return success(None)
            case CoffeeScheduleInput():
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


class CoffeeCommand(EffectCommand[CoffeeInput, CoffeeRequest]):
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
            CoffeeRequestParser(),
            (
                TelegramIdentityValidator(),
                ActiveUserValidator(active_users),
            ),
            (CoffeeScheduleScopeValidator(access),),
            CoffeeRequestResolver(coffee_time),
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
                user = self._active_users.require_active(profile.telegram_user_id)
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
                user = self._active_users.require_active(profile.telegram_user_id)
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
