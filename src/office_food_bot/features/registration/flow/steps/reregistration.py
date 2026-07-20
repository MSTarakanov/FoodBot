from __future__ import annotations

from office_food_bot.features.registration.flow.draft import RegistrationDraft
from office_food_bot.features.registration.flow.identifiers import RegistrationStepId
from office_food_bot.features.registration.flow.steps.base import RegistrationStep
from office_food_bot.features.registration.flow.use_case import RegistrationFlowUseCase
from office_food_bot.features.registration.flow.validation import (
    RegistrationStepErrorCode,
    TextFlowInput,
    confirmation_value,
)
from office_food_bot.flows.contracts import (
    FlowContext,
    FlowStepParser,
    FlowStepValidator,
    FlowTransition,
)


class RegistrationConfirmationStep(RegistrationStep[TextFlowInput]):
    step_id = RegistrationStepId.REREGISTRATION_CONFIRMATION

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
        return await self._use_case.confirm_reregistration(
            context,
            draft,
            confirmed=confirmation_value(value),
        )
