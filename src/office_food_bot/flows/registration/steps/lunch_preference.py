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
from office_food_bot.flows.registration.identifiers import RegistrationStepId
from office_food_bot.flows.registration.rendering import coffee_preference_view
from office_food_bot.flows.registration.steps.base import RegistrationStep
from office_food_bot.flows.registration.validation import (
    RegistrationStepErrorCode,
    TextFlowInput,
    yes_no_value,
)


class RegistrationLunchPreferenceStep(RegistrationStep[TextFlowInput]):
    step_id = RegistrationStepId.LUNCH_PREFERENCE

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
    ) -> None:
        super().__init__(parser, validators)

    async def advance(
        self,
        context: FlowContext,
        draft: RegistrationDraft,
        value: TextFlowInput,
    ) -> FlowTransition:
        return MoveToStep(
            RegistrationStepId.COFFEE_PREFERENCE,
            replace(draft, lunch_invitations_enabled=yes_no_value(value)),
            coffee_preference_view(),
        )
