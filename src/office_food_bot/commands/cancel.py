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
from office_food_bot.controllers.registration import cancel_registration_command


class CancelCommand(EffectCommand[RawArguments]):
    definition = CommandDefinition(
        "cancel",
        "отменить текущий сценарий",
        "/cancel",
        CommandScope.PRIVATE,
        HelpSection.SERVICE,
        flow_policy=CommandFlowPolicy.MANAGED_BY_COMMAND,
    )

    def __init__(self) -> None:
        super().__init__(RawArgumentsParser(), (), ())

    async def execute_effect(
        self,
        context: CommandContext,
        request: RawArguments,
    ) -> None:
        await cancel_registration_command(
            context.message,
            context.messenger,
            context.state,
        )
