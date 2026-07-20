from __future__ import annotations

from office_food_bot.features.registration.flow.draft import RegistrationDraft
from office_food_bot.features.registration.flow.identifiers import (
    RegistrationFlowId,
    RegistrationStepId,
)
from office_food_bot.features.registration.flow.rendering import (
    NAME_PROMPT_TEXT,
    name_prompt_view,
)
from office_food_bot.features.registration.flow.requests import (
    RegisterOtherRequest,
    RegisterRequest,
    RegisterSelfRequest,
)
from office_food_bot.features.registration.service import RegistrationService
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


class RegistrationFlow(StartableFlow[RegisterRequest]):
    flow_id = RegistrationFlowId.REGISTRATION

    def __init__(
        self,
        registration: RegistrationService,
        steps: tuple[FlowStep[RegistrationStepId, RegistrationDraft], ...],
    ) -> None:
        step_ids = tuple(step.step_id for step in steps)
        if not step_ids:
            raise ValueError("Registration flow requires at least one step")
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("Registration flow step ids must be unique")
        self._registration = registration
        self._steps_by_id = {step.step_id: step for step in steps}

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
        match request:
            case RegisterSelfRequest():
                pass
            case RegisterOtherRequest():
                target = self._registration.registration_profile_for_telegram_id(
                    request.telegram_user_id
                )
                prompt = (
                    "Регистрируем пользователя Telegram ID "
                    f"{request.telegram_user_id}.\n\n{NAME_PROMPT_TEXT}"
                )
            case _:
                raise RuntimeError(
                    f"Unsupported registration request: {type(request).__name__}"
                )
        draft = RegistrationDraft(target=target)
        return MoveToStep(
            RegistrationStepId.NAME,
            draft,
            name_prompt_view(target, prompt),
        )

    async def handle(
        self,
        context: FlowContext,
        session: FlowSession,
    ) -> FlowTransition:
        match session.step_id:
            case RegistrationStepId():
                step_id = session.step_id
            case _:
                raise RuntimeError(
                    "Registration flow received unsupported step id: "
                    f"{session.step_id}"
                )
        step = self._steps_by_id.get(step_id)
        if step is None:
            raise RuntimeError(f"Unknown registration step: {step_id}")
        match session.draft:
            case RegistrationDraft():
                return await step.handle(context, session.draft)
            case _:
                raise RuntimeError(
                    "Registration flow received unsupported draft: "
                    f"{type(session.draft).__name__}"
                )

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
