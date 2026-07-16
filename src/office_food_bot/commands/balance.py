from __future__ import annotations

from office_food_bot.balance_models import BalanceReport
from office_food_bot.commanding.contracts import (
    CommandContext,
    NoArguments,
    NoArgumentsParser,
    RenderedCommand,
)
from office_food_bot.commanding.definition import (
    CommandDefinition,
    CommandScope,
    HelpSection,
)
from office_food_bot.commanding.validators import (
    ActiveUserValidator,
    TelegramIdentityValidator,
)
from office_food_bot.messaging import BotMessenger
from office_food_bot.presenters import render_balance_message
from office_food_bot.services.balances import BalanceService
from office_food_bot.services.user_access import ActiveUserResolver


class BalanceCommand(RenderedCommand[NoArguments, BalanceReport]):
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
        balances: BalanceService,
        active_users: ActiveUserResolver,
    ) -> None:
        super().__init__(
            messenger,
            NoArgumentsParser(),
            (TelegramIdentityValidator(),),
            (ActiveUserValidator(active_users),),
            render_balance_message,
        )
        self._balances = balances

    async def execute(
        self,
        context: CommandContext,
        request: NoArguments,
    ) -> BalanceReport:
        del context, request
        return await self._balances.balance()
