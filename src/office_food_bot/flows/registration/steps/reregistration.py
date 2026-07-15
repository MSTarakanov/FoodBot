from __future__ import annotations

from office_food_bot.flows.contracts import (
    FlowContext,
    FlowStepParser,
    FlowStepValidator,
    FlowTransition,
)
from office_food_bot.flows.registration.draft import RegistrationDraft
from office_food_bot.flows.registration.steps.base import RegistrationStep
from office_food_bot.flows.registration.steps.ids import REREGISTRATION_STEP_ID
from office_food_bot.flows.registration.use_case import RegistrationFlowUseCase
from office_food_bot.flows.registration.validation import TextFlowInput, yes_no_value


class RegistrationConfirmationStep(RegistrationStep[TextFlowInput]):
    step_id = REREGISTRATION_STEP_ID

    def __init__(
        self,
        parser: FlowStepParser[TextFlowInput],
        validators: tuple[
            FlowStepValidator[RegistrationDraft, TextFlowInput],
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
            confirmed=yes_no_value(value),
        )
