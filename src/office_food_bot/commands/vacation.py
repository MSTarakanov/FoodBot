from __future__ import annotations

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
from office_food_bot.commanding.errors.models import CommandInputError, InputErrorCode
from office_food_bot.commanding.validators import (
    ActiveUserValidator,
    TelegramIdentityValidator,
    require_telegram_profile,
)
from office_food_bot.messaging import BotMessenger
from office_food_bot.presenters.vacation import render_vacation_report
from office_food_bot.services.user_access import ActiveUserResolver
from office_food_bot.services.vacation import (
    VacationRequest,
    VacationRequestKind,
    VacationService,
    parse_vacation_request,
)
from office_food_bot.vacation_models import VacationReport

VACATION_DATE_FORMAT_ERROR_TEXT = (
    "Не понял дату. Напиши количество дней или дату: "
    "/vacation 2, /vacation 20.07, /vacation 2026-07-20"
)


class VacationRequestParser:
    def __init__(self, vacation: VacationService) -> None:
        self._vacation = vacation

    def parse(self, raw_arguments: str | None) -> VacationRequest:
        request = parse_vacation_request(
            raw_arguments or "",
            self._vacation.local_today(),
        )
        if request.kind == VacationRequestKind.INVALID:
            raise CommandInputError(InputErrorCode.INVALID_FORMAT)
        return request


class VacationCommand(RenderedCommand[VacationRequest, VacationReport]):
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
        vacation: VacationService,
        active_users: ActiveUserResolver,
    ) -> None:
        super().__init__(
            messenger,
            VacationRequestParser(vacation),
            (TelegramIdentityValidator(),),
            (ActiveUserValidator(active_users),),
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
