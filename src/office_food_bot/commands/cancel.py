from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    RawArguments,
    RawArgumentsParser,
)
from office_food_bot.commanding.definition import (
    CommandDefinition,
    CommandFlowPolicy,
    CommandScope,
    HelpSection,
)
from office_food_bot.flows.runner import FlowRunner


class CancelCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "cancel",
        "отменить текущий сценарий",
        "/cancel",
        CommandScope.PRIVATE,
        HelpSection.SERVICE,
        flow_policy=CommandFlowPolicy.MANAGED_BY_COMMAND,
    )

    def __init__(self, runner: FlowRunner) -> None:
        super().__init__(RawArgumentsParser(), (), ())
        self._runner = runner

    async def execute_effect(
        self,
        context: CommandContext,
        request: RawArguments,
    ) -> None:
        await self._runner.cancel(context)
