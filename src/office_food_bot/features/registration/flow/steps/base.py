from __future__ import annotations

from office_food_bot.features.registration.flow.draft import RegistrationDraft
from office_food_bot.features.registration.flow.identifiers import RegistrationStepId
from office_food_bot.features.registration.flow.rendering import validation_error_view
from office_food_bot.features.registration.flow.validation import RegistrationStepErrorCode
from office_food_bot.flows.contracts import (
    FlowStepParser,
    FlowStepValidator,
    FlowView,
    ParsedFlowStep,
)


class RegistrationStep[InputT](
    ParsedFlowStep[
        RegistrationStepId,
        RegistrationDraft,
        InputT,
        RegistrationStepErrorCode,
    ]
):
    def __init__(
        self,
        parser: FlowStepParser[InputT],
        validators: tuple[
            FlowStepValidator[RegistrationDraft, InputT, RegistrationStepErrorCode],
            ...,
        ],
    ) -> None:
        super().__init__(parser, validators)

    def render_validation_error(
        self,
        error: RegistrationStepErrorCode,
        draft: RegistrationDraft,
    ) -> FlowView:
        return validation_error_view(error)
