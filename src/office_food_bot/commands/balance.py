from __future__ import annotations

from office_food_bot.balance_models import BalanceReport
from office_food_bot.commanding.contracts import (
    CommandContext,
    RawArguments,
    RawArgumentsParser,
    RenderedCommand,
)
from office_food_bot.commanding.definition import (
    CommandDefinition,
    CommandScope,
    HelpSection,
)
from office_food_bot.commanding.validators import (
    ActiveUserValidator,
)
from office_food_bot.presenters import render_balance_message
from office_food_bot.services.balances import BalanceService
from office_food_bot.services.user_access import ActiveUserResolver


class BalanceCommand(RenderedCommand[RawArguments, BalanceReport]):
    definition = CommandDefinition(
        "balance",
        "показать баланс Splitwise",
        "/balance",
        CommandScope.ANY,
        HelpSection.MAIN,
    )

    def __init__(
        self,
        balances: BalanceService,
        active_users: ActiveUserResolver,
    ) -> None:
        super().__init__(
            RawArgumentsParser(),
            (ActiveUserValidator(active_users),),
            (),
            render_balance_message,
        )
        self._balances = balances

    async def execute(
        self,
        context: CommandContext,
        request: RawArguments,
    ) -> BalanceReport:
        del context, request
        return await self._balances.balance()
