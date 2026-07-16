from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    NoArguments,
    NoArgumentsParser,
)
from office_food_bot.commanding.definition import (
    CommandDefinition,
    CommandFlowPolicy,
    CommandScope,
    HelpSection,
)
from office_food_bot.commanding.errors.models import CommonErrorCode
from office_food_bot.commanding.errors.rendering import ErrorRenderer
from office_food_bot.flows.runner import FlowRunner
from office_food_bot.messaging import BotMessenger


class CancelCommand(EffectCommand[NoArguments]):
    definition = CommandDefinition(
        "cancel",
        "отменить текущий сценарий",
        "/cancel",
        CommandScope.PRIVATE,
        HelpSection.SERVICE,
        flow_policy=CommandFlowPolicy.MANAGED_BY_COMMAND,
    )

    def __init__(
        self,
        messenger: BotMessenger,
        common_error_renderer: ErrorRenderer[CommonErrorCode],
        runner: FlowRunner,
    ) -> None:
        super().__init__(messenger, common_error_renderer, NoArgumentsParser(), (), ())
        self._runner = runner

    async def execute_effect(
        self,
        context: CommandContext,
        request: NoArguments,
    ) -> None:
        del request
        await self._runner.cancel(context)
