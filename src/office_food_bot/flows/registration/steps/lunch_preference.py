from __future__ import annotations

from dataclasses import replace

from office_food_bot.flows.contracts import (
    FlowContext,
    FlowStepParser,
    FlowStepValidator,
    FlowTransition,
    MoveToStep,
)
from office_food_bot.flows.registration.draft import RegistrationDraft
from office_food_bot.flows.registration.rendering import coffee_preference_view
from office_food_bot.flows.registration.steps.base import RegistrationStep
from office_food_bot.flows.registration.steps.ids import (
    COFFEE_PREFERENCE_STEP_ID,
    LUNCH_PREFERENCE_STEP_ID,
)
from office_food_bot.flows.registration.validation import TextFlowInput, yes_no_value


class RegistrationLunchPreferenceStep(RegistrationStep[TextFlowInput]):
    step_id = LUNCH_PREFERENCE_STEP_ID

    def __init__(
        self,
        parser: FlowStepParser[TextFlowInput],
        validators: tuple[
            FlowStepValidator[RegistrationDraft, TextFlowInput],
            ...,
        ],
    ) -> None:
        super().__init__(parser, validators)

    async def advance(
        self,
        context: FlowContext,
        draft: RegistrationDraft,
        value: TextFlowInput,
    ) -> FlowTransition:
        return MoveToStep(
            COFFEE_PREFERENCE_STEP_ID,
            replace(draft, lunch_invitations_enabled=yes_no_value(value)),
            coffee_preference_view(),
        )
