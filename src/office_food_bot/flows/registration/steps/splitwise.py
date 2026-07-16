from __future__ import annotations

from dataclasses import replace

from office_food_bot.flows.contracts import (
    FlowContext,
    FlowStepParser,
    FlowStepValidator,
    FlowTransition,
    MoveToStep,
    StayOnStep,
)
from office_food_bot.flows.registration.draft import RegistrationDraft
from office_food_bot.flows.registration.identifiers import RegistrationStepId
from office_food_bot.flows.registration.rendering import (
    lunch_preference_view,
    splitwise_not_found_view,
    splitwise_unavailable_view,
)
from office_food_bot.flows.registration.steps.base import RegistrationStep
from office_food_bot.flows.registration.use_case import RegistrationFlowUseCase
from office_food_bot.flows.registration.validation import (
    RegistrationStepErrorCode,
    TextFlowInput,
    is_splitwise_skip,
    required_text,
)
from office_food_bot.models import SplitwiseMember
from office_food_bot.services.registration import RegistrationService
from office_food_bot.services.splitwise import SplitwiseLookupKind, SplitwiseService


class RegistrationSplitwiseStep(RegistrationStep[TextFlowInput]):
    step_id = RegistrationStepId.SPLITWISE

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
        splitwise: SplitwiseService,
        use_case: RegistrationFlowUseCase,
    ) -> None:
        super().__init__(parser, validators)
        self._registration = registration
        self._splitwise = splitwise
        self._use_case = use_case

    async def advance(
        self,
        context: FlowContext,
        draft: RegistrationDraft,
        value: TextFlowInput,
    ) -> FlowTransition:
        if is_splitwise_skip(value):
            return await self._continue(context, draft, None)

        result = await self._splitwise.find_member_by_email(required_text(value))
        if result.kind == SplitwiseLookupKind.FOUND and result.member is not None:
            return await self._continue(context, draft, result.member)
        if result.kind == SplitwiseLookupKind.NOT_FOUND:
            return StayOnStep(splitwise_not_found_view())
        return StayOnStep(splitwise_unavailable_view())

    async def _continue(
        self,
        context: FlowContext,
        draft: RegistrationDraft,
        splitwise_member: SplitwiseMember | None,
    ) -> FlowTransition:
        updated_draft = replace(draft, splitwise_member=splitwise_member)
        if not self._registration.should_ask_initial_preferences(
            draft.target.telegram_user_id
        ):
            return await self._use_case.complete(context, updated_draft)
        return MoveToStep(
            RegistrationStepId.LUNCH_PREFERENCE,
            updated_draft,
            lunch_preference_view(splitwise_member),
        )
