from __future__ import annotations

from office_food_bot.flows.contracts import (
    FlowStepParser,
    FlowStepValidator,
    FlowView,
    ParsedFlowStep,
)
from office_food_bot.flows.registration.draft import RegistrationDraft
from office_food_bot.flows.registration.identifiers import RegistrationStepId
from office_food_bot.flows.registration.rendering import validation_error_view
from office_food_bot.flows.registration.validation import RegistrationStepErrorCode


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
