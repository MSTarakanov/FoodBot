from __future__ import annotations

from office_food_bot.flows.contracts import (
    ClosingFlowView,
    CompleteFlow,
    FlowContext,
    FlowSession,
    FlowStep,
    FlowTransition,
    MoveToStep,
    StartableFlow,
)
from office_food_bot.flows.registration.draft import RegistrationDraft
from office_food_bot.flows.registration.rendering import (
    NAME_PROMPT_TEXT,
    name_prompt_view,
)
from office_food_bot.flows.registration.requests import (
    RegisterOtherRequest,
    RegisterRequest,
)
from office_food_bot.flows.registration.steps.ids import NAME_STEP_ID
from office_food_bot.services.registration import RegistrationService


class RegistrationFlow(StartableFlow[RegisterRequest]):
    name = "registration"

    def __init__(
        self,
        registration: RegistrationService,
        steps: tuple[FlowStep, ...],
    ) -> None:
        step_ids = tuple(step.step_id for step in steps)
        if not step_ids:
            raise ValueError("Registration flow requires at least one step")
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("Registration flow step ids must be unique")
        self._registration = registration
        self._steps = {step.step_id: step for step in steps}

    async def start(
        self,
        context: FlowContext,
        request: RegisterRequest,
    ) -> FlowTransition:
        actor = context.profile
        if actor is None:
            raise RuntimeError("Registration flow started without Telegram identity")

        target = actor
        prompt = NAME_PROMPT_TEXT
        if isinstance(request, RegisterOtherRequest):
            target = self._registration.registration_profile_for_telegram_id(
                request.telegram_user_id
            )
            prompt = (
                f"Регистрируем пользователя Telegram ID {request.telegram_user_id}.\n\n"
                f"{NAME_PROMPT_TEXT}"
            )
        draft = RegistrationDraft(target=target)
        return MoveToStep(
            NAME_STEP_ID,
            draft,
            name_prompt_view(target, prompt),
        )

    async def handle(
        self,
        context: FlowContext,
        session: FlowSession,
    ) -> FlowTransition:
        step = self._steps.get(session.step_id)
        if step is None:
            raise RuntimeError(f"Unknown registration step: {session.step_id}")
        return await step.handle(context, session.draft)

    async def cancel(
        self,
        context: FlowContext,
        session: FlowSession,
    ) -> FlowTransition:
        return CompleteFlow(ClosingFlowView("Текущий сценарий отменен."))

    async def abort(
        self,
        context: FlowContext,
        session: FlowSession,
    ) -> None:
        return None
