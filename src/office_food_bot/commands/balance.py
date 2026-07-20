from __future__ import annotations

from office_food_bot.application.users.resolver import ActiveUserResolver
from office_food_bot.commanding.contracts import (
    CommandContext,
    IdentityResolver,
    NoArguments,
    NoArgumentsParser,
    ResultRenderedCommand,
)
from office_food_bot.commanding.definition import (
    CommandDefinition,
    CommandScope,
    HelpSection,
)
from office_food_bot.commanding.errors.models import CommonErrorCode
from office_food_bot.commanding.errors.rendering import ErrorRenderer
from office_food_bot.commanding.validators import (
    ActiveUserValidator,
    TelegramIdentityValidator,
)
from office_food_bot.features.balance.errors import BalanceErrorCode
from office_food_bot.features.balance.models import BalanceReport
from office_food_bot.features.balance.rendering import render_balance_message
from office_food_bot.features.balance.use_case import GetBalanceReport
from office_food_bot.messaging import BotMessenger
from office_food_bot.result import Result


class BalanceCommand(
    ResultRenderedCommand[
        NoArguments,
        NoArguments,
        BalanceReport,
        BalanceErrorCode,
    ]
):
    definition = CommandDefinition(
        "balance",
        "показать баланс Splitwise",
        "/balance",
        CommandScope.ANY,
        HelpSection.MAIN,
    )

    def __init__(
        self,
        messenger: BotMessenger,
        common_error_renderer: ErrorRenderer[CommonErrorCode],
        get_balance_report: GetBalanceReport,
        active_users: ActiveUserResolver,
        error_renderer: ErrorRenderer[BalanceErrorCode],
    ) -> None:
        super().__init__(
            messenger,
            common_error_renderer,
            NoArgumentsParser(),
            (
                TelegramIdentityValidator(),
                ActiveUserValidator(active_users),
            ),
            (),
            IdentityResolver(),
            render_balance_message,
            error_renderer,
        )
        self._get_balance_report = get_balance_report

    async def execute(
        self,
        _context: CommandContext,
        _request: NoArguments,
    ) -> Result[BalanceReport, BalanceErrorCode]:
        return await self._get_balance_report.execute()
