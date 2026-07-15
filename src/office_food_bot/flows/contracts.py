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


class FlowStepError(Exception):
    pass


class FlowStepParser[InputT](Protocol):
    def parse(self, message: Message) -> InputT: ...


class FlowStepValidator[DraftT: FlowDraft, InputT](Protocol):
    def validate(
        self,
        context: FlowContext,
        draft: DraftT,
        value: InputT,
    ) -> None: ...


class FlowStep[StepIdT: FlowStepId](ABC):
    step_id: StepIdT

    @abstractmethod
    async def handle(
        self,
        context: FlowContext,
        draft: FlowDraft,
    ) -> FlowTransition: ...


class ParsedFlowStep[
    StepIdT: FlowStepId,
    DraftT: FlowDraft,
    InputT,
](FlowStep[StepIdT], ABC):
    def __init__(
        self,
        draft_type: type[DraftT],
        parser: FlowStepParser[InputT],
        validators: tuple[FlowStepValidator[DraftT, InputT], ...],
    ) -> None:
        self._draft_type = draft_type
        self._parser = parser
        self._validators = validators

    @final
    async def handle(
        self,
        context: FlowContext,
        draft: FlowDraft,
    ) -> FlowTransition:
        if not isinstance(draft, self._draft_type):
            raise RuntimeError(
                f"Step {self.step_id} received unsupported draft {type(draft).__name__}"
            )

        try:
            value = self._parser.parse(context.message)
            for validator in self._validators:
                validator.validate(context, draft, value)
        except FlowStepError as error:
            return StayOnStep(self.render_validation_error(error, draft))

        return await self.advance(context, draft, value)

    @abstractmethod
    def render_validation_error(
        self,
        error: FlowStepError,
        draft: DraftT,
    ) -> FlowView: ...

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
