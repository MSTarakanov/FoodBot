from __future__ import annotations

from dataclasses import dataclass
from typing import assert_never

from office_food_bot.commanding.contracts import (
    CommandContext,
    RenderedCommand,
)
from office_food_bot.commanding.definition import (
    CommandDefinition,
    CommandHelpEntry,
    CommandInputMessage,
    CommandScope,
    HelpSection,
)
from office_food_bot.commanding.errors.models import CommonErrorCode, InputErrorCode
from office_food_bot.commanding.errors.rendering import ErrorRenderer
from office_food_bot.commanding.validators import (
    ActiveUserValidator,
    TelegramIdentityValidator,
    require_telegram_profile,
)
from office_food_bot.features.users.access import ActiveUserResolver
from office_food_bot.features.vacation.models import VacationReport
from office_food_bot.features.vacation.rendering import render_vacation_report
from office_food_bot.features.vacation.service import (
    VacationRequest,
    VacationRequestKind,
    VacationService,
    parse_vacation_request,
)
from office_food_bot.messaging import BotMessenger
from office_food_bot.result import Result, failure, success

VACATION_DATE_FORMAT_ERROR_TEXT = (
    "Не понял дату. Напиши количество дней или дату: "
    "/vacation 2, /vacation 20.07, /vacation 2026-07-20"
)


@dataclass(frozen=True, slots=True)
class VacationInput:
    raw_value: str


class VacationRequestParser:

    def parse(
        self,
        raw_arguments: str | None,
    ) -> VacationInput:
        return VacationInput(raw_arguments or "")


class VacationRequestResolver:
    def __init__(self, vacation: VacationService) -> None:
        self._vacation = vacation

    def resolve(
        self,
        value: VacationInput,
    ) -> Result[VacationRequest, InputErrorCode]:
        request = parse_vacation_request(
            value.raw_value,
            self._vacation.local_today(),
        )
        match request.kind:
            case VacationRequestKind.INVALID:
                return failure(InputErrorCode.INVALID_FORMAT)
            case (
                VacationRequestKind.STATUS
                | VacationRequestKind.CLEAR
                | VacationRequestKind.SET
            ):
                return success(request)
        assert_never(request.kind)


class VacationCommand(
    RenderedCommand[VacationInput, VacationRequest, VacationReport]
):
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
        input_errors=(
            CommandInputMessage(
                InputErrorCode.INVALID_FORMAT,
                VACATION_DATE_FORMAT_ERROR_TEXT,
            ),
        ),
    )

    def __init__(
        self,
        messenger: BotMessenger,
        common_error_renderer: ErrorRenderer[CommonErrorCode],
        vacation: VacationService,
        active_users: ActiveUserResolver,
    ) -> None:
        super().__init__(
            messenger,
            common_error_renderer,
            VacationRequestParser(),
            (
                TelegramIdentityValidator(),
                ActiveUserValidator(active_users),
            ),
            (),
            VacationRequestResolver(vacation),
            render_vacation_report,
        )
        self._vacation = vacation

    async def execute(
        self,
        context: CommandContext,
        request: VacationRequest,
    ) -> VacationReport:
        profile = require_telegram_profile(context)
        return self._vacation.execute(profile.telegram_user_id, request)
