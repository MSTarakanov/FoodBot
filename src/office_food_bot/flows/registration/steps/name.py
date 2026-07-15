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
from office_food_bot.flows.registration.rendering import splitwise_prompt_view
from office_food_bot.flows.registration.steps.base import RegistrationStep
from office_food_bot.flows.registration.steps.ids import NAME_STEP_ID, SPLITWISE_STEP_ID
from office_food_bot.flows.registration.validation import TextFlowInput, required_text
from office_food_bot.services.registration import RegistrationService


class RegistrationNameStep(RegistrationStep[TextFlowInput]):
    step_id = NAME_STEP_ID

    def __init__(
        self,
        parser: FlowStepParser[TextFlowInput],
        validators: tuple[
            FlowStepValidator[RegistrationDraft, TextFlowInput],
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
            SPLITWISE_STEP_ID,
            replace(
                draft,
                target=profile,
                requested_display_name=display_name,
            ),
            splitwise_prompt_view(display_name),
        )
