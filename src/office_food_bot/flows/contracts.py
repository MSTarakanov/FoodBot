from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, final

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.messaging import BotMessenger
from office_food_bot.models import TelegramProfile
from office_food_bot.result import Result, success


class FlowId(StrEnum):
    pass


class FlowStepId(StrEnum):
    pass


@dataclass(frozen=True, slots=True)
class FlowDraft:
    pass


@dataclass(frozen=True, slots=True)
class FlowSession:
    flow_id: FlowId
    step_id: FlowStepId
    draft: FlowDraft


@dataclass(frozen=True, slots=True)
class FlowContext:
    message: Message
    bot: Bot
    messenger: BotMessenger
    state: FSMContext
    profile: TelegramProfile | None


@dataclass(frozen=True, slots=True)
class FlowView:
    pass


@dataclass(frozen=True, slots=True)
class TextFlowView(FlowView):
    text: str


@dataclass(frozen=True, slots=True)
class ChoiceFlowView(FlowView):
    text: str
    choices: tuple[str, ...]
    columns: int = 2
    one_time_keyboard: bool = True


@dataclass(frozen=True, slots=True)
class ClosingFlowView(FlowView):
    text: str


class FlowPostAction(Protocol):
    async def execute(self, context: FlowContext) -> None: ...


@dataclass(frozen=True, slots=True)
class FlowTransition:
    pass


@dataclass(frozen=True, slots=True)
class StayOnStep(FlowTransition):
    view: FlowView


@dataclass(frozen=True, slots=True)
class MoveToStep(FlowTransition):
    step_id: FlowStepId
    draft: FlowDraft
    view: FlowView


@dataclass(frozen=True, slots=True)
class CompleteFlow(FlowTransition):
    view: FlowView | None
    post_action: FlowPostAction | None = None


class FlowStepParser[InputT](Protocol):
    def parse(self, message: Message) -> InputT: ...


class FlowStepValidator[DraftT: FlowDraft, InputT, ErrorT](Protocol):
    def validate(
        self,
        context: FlowContext,
        draft: DraftT,
        value: InputT,
    ) -> Result[None, ErrorT]: ...


class FlowStep[StepIdT: FlowStepId, DraftT: FlowDraft](ABC):
    step_id: StepIdT

    @abstractmethod
    async def handle(
        self,
        context: FlowContext,
        draft: DraftT,
    ) -> FlowTransition: ...


class ParsedFlowStep[
    StepIdT: FlowStepId,
    DraftT: FlowDraft,
    InputT,
    ErrorT,
](FlowStep[StepIdT, DraftT], ABC):
    def __init__(
        self,
        parser: FlowStepParser[InputT],
        validators: tuple[FlowStepValidator[DraftT, InputT, ErrorT], ...],
    ) -> None:
        self._parser = parser
        self._validators = validators

    @final
    async def handle(
        self,
        context: FlowContext,
        draft: DraftT,
    ) -> FlowTransition:
        value = self._parser.parse(context.message)
        validation = _validate_flow_input(
            context,
            draft,
            value,
            self._validators,
        )
        return await validation.fold(
            lambda _: self.advance(context, draft, value),
            lambda error: self._validation_failure(error, draft),
        )

    @abstractmethod
    def render_validation_error(
        self,
        error: ErrorT,
        draft: DraftT,
    ) -> FlowView: ...

    async def _validation_failure(
        self,
        error: ErrorT,
        draft: DraftT,
    ) -> FlowTransition:
        return StayOnStep(self.render_validation_error(error, draft))

    @abstractmethod
    async def advance(
        self,
        context: FlowContext,
        draft: DraftT,
        value: InputT,
    ) -> FlowTransition: ...


class ActiveFlow(ABC):
    flow_id: FlowId

    @abstractmethod
    async def handle(
        self,
        context: FlowContext,
        session: FlowSession,
    ) -> FlowTransition: ...

    @abstractmethod
    async def cancel(
        self,
        context: FlowContext,
        session: FlowSession,
    ) -> FlowTransition: ...

    @abstractmethod
    async def abort(
        self,
        context: FlowContext,
        session: FlowSession,
    ) -> None: ...


class StartableFlow[RequestT](ActiveFlow, ABC):
    @abstractmethod
    async def start(
        self,
        context: FlowContext,
        request: RequestT,
    ) -> FlowTransition: ...


def _validate_flow_input[DraftT: FlowDraft, InputT, ErrorT](
    context: FlowContext,
    draft: DraftT,
    value: InputT,
    validators: tuple[FlowStepValidator[DraftT, InputT, ErrorT], ...],
) -> Result[None, ErrorT]:
    result: Result[None, ErrorT] = success(None)
    for validator in validators:

        def validate_next(
            _: None,
            current: FlowStepValidator[DraftT, InputT, ErrorT] = validator,
        ) -> Result[None, ErrorT]:
            return current.validate(context, draft, value)

        result = result.and_then(validate_next)
    return result
