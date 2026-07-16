from __future__ import annotations

from dataclasses import replace

from office_food_bot.flows.contracts import (
    FlowContext,
    FlowStepParser,
    FlowStepValidator,
    FlowTransition,
)
from office_food_bot.flows.registration.draft import RegistrationDraft
from office_food_bot.flows.registration.identifiers import RegistrationStepId
from office_food_bot.flows.registration.steps.base import RegistrationStep
from office_food_bot.flows.registration.use_case import RegistrationFlowUseCase
from office_food_bot.flows.registration.validation import (
    RegistrationStepErrorCode,
    TextFlowInput,
    yes_no_value,
)


class RegistrationCoffeePreferenceStep(RegistrationStep[TextFlowInput]):
    step_id = RegistrationStepId.COFFEE_PREFERENCE

    def __init__(
        self,
        parser: FlowStepParser[TextFlowInput],
        validators: tuple[
            FlowStepValidator[
                RegistrationDraft,
                TextFlowInput,
                RegistrationStepErrorCode,
            ],
            ...,
        ],
        use_case: RegistrationFlowUseCase,
    ) -> None:
        super().__init__(parser, validators)
        self._use_case = use_case

    async def advance(
        self,
        context: FlowContext,
        draft: RegistrationDraft,
        value: TextFlowInput,
    ) -> FlowTransition:
        if draft.lunch_invitations_enabled is None:
            raise RuntimeError("Registration flow has no lunch preference")
        return await self._use_case.complete(
            context,
            replace(draft, coffee_invitations_enabled=yes_no_value(value)),
        )
