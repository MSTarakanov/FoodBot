from __future__ import annotations

from office_food_bot.flows.contracts import (
    FlowStepError,
    FlowStepParser,
    FlowStepValidator,
    FlowView,
    ParsedFlowStep,
)
from office_food_bot.flows.registration.draft import RegistrationDraft
from office_food_bot.flows.registration.identifiers import RegistrationStepId
from office_food_bot.flows.registration.rendering import validation_error_view
from office_food_bot.flows.registration.validation import RegistrationStepError


class RegistrationStep[InputT](
    ParsedFlowStep[RegistrationStepId, RegistrationDraft, InputT]
):
    def __init__(
        self,
        parser: FlowStepParser[InputT],
        validators: tuple[FlowStepValidator[RegistrationDraft, InputT], ...],
    ) -> None:
        super().__init__(RegistrationDraft, parser, validators)

    def render_validation_error(
        self,
        error: FlowStepError,
        draft: RegistrationDraft,
    ) -> FlowView:
        if not isinstance(error, RegistrationStepError):
            raise RuntimeError(
                f"Unsupported registration validation error: {type(error).__name__}"
            )
        return validation_error_view(error)
