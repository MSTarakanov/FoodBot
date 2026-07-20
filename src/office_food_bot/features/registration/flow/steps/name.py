from __future__ import annotations

from dataclasses import replace

from office_food_bot.features.registration.flow.draft import RegistrationDraft
from office_food_bot.features.registration.flow.identifiers import RegistrationStepId
from office_food_bot.features.registration.flow.rendering import splitwise_prompt_view
from office_food_bot.features.registration.flow.steps.base import RegistrationStep
from office_food_bot.features.registration.flow.validation import (
    RegistrationStepErrorCode,
    TextFlowInput,
    required_text,
)
from office_food_bot.features.registration.service import RegistrationService
from office_food_bot.flows.contracts import (
    FlowContext,
    FlowStepParser,
    FlowStepValidator,
    FlowTransition,
    MoveToStep,
)


class RegistrationNameStep(RegistrationStep[TextFlowInput]):
    step_id = RegistrationStepId.NAME

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
        registration: RegistrationService,
    ) -> None:
        super().__init__(parser, validators)
        self._registration = registration

    async def advance(
        self,
        context: FlowContext,
        draft: RegistrationDraft,
        value: TextFlowInput,
    ) -> FlowTransition:
        profile = draft.target_for_current_message(context.profile)
        display_name = self._registration.display_name_from_input(
            profile,
            required_text(value),
        )
        return MoveToStep(
            RegistrationStepId.SPLITWISE,
            replace(
                draft,
                target=profile,
                requested_display_name=display_name,
            ),
            splitwise_prompt_view(display_name),
        )
