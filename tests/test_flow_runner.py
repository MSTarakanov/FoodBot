from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import auto

import pytest
from aiogram import Bot
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat, Message, User

from office_food_bot.commanding.contracts import CommandContext
from office_food_bot.commanding.invocation import ParsedCommand
from office_food_bot.flows.catalog import FlowCatalog
from office_food_bot.flows.contracts import (
    ClosingFlowView,
    CompleteFlow,
    FlowContext,
    FlowDraft,
    FlowId,
    FlowPostAction,
    FlowSession,
    FlowStepError,
    FlowStepId,
    MoveToStep,
    ParsedFlowStep,
    StartableFlow,
    StayOnStep,
    TextFlowView,
)
from office_food_bot.flows.runner import ActiveFlowState, FlowRunner
from office_food_bot.messaging import BotMessenger
from office_food_bot.models import TelegramProfile


class RecordingFlowMessenger(BotMessenger):
    def __init__(self, events: list[str]) -> None:
        self.events = events

    async def reply(self, message: Message, text: str, **kwargs) -> Message:
        self.events.append(f"reply:{text}")
        return message

    async def reply_with_choices(
        self,
        message: Message,
        text: str,
        choices: tuple[str, ...],
        **kwargs,
    ) -> Message:
        self.events.append(f"choices:{text}:{','.join(choices)}")
        return message


@dataclass(frozen=True, slots=True)
class FixtureDraft(FlowDraft):
    value: str


class FixtureFlowId(FlowId):
    FIXTURE = auto()


class FixtureStepId(FlowStepId):
    INPUT = auto()
    NEXT = auto()
    FIXTURE = auto()


class FixturePostAction(FlowPostAction):
    def __init__(self, events: list[str]) -> None:
        self._events = events

    async def execute(self, context: FlowContext) -> None:
        self._events.append("post")


class FixtureFlow(StartableFlow[str]):
    flow_id = FixtureFlowId.FIXTURE

    def __init__(self, events: list[str]) -> None:
        self._events = events

    async def start(self, context: FlowContext, request: str):
        self._events.append(f"start:{request}")
        return MoveToStep(
            FixtureStepId.INPUT,
            FixtureDraft(request),
            TextFlowView("started"),
        )

    async def handle(self, context: FlowContext, session: FlowSession):
        self._events.append(f"handle:{session.step_id}")
        return CompleteFlow(
            ClosingFlowView("done"),
            FixturePostAction(self._events),
        )

    async def cancel(self, context: FlowContext, session: FlowSession):
        self._events.append(f"cancel:{session.step_id}")
        return CompleteFlow(ClosingFlowView("cancelled"))

    async def abort(self, context: FlowContext, session: FlowSession) -> None:
        self._events.append(f"abort:{session.step_id}")


class FixtureStepError(FlowStepError):
    pass


class FixtureStepParser:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def parse(self, message: Message) -> str:
        self._events.append("parse")
        return message.text or ""


class FixtureStepValidator:
    def __init__(self, events: list[str], *, fails: bool = False) -> None:
        self._events = events
        self._fails = fails

    def validate(self, context: FlowContext, draft: FixtureDraft, value: str) -> None:
        self._events.append("validate")
        if self._fails:
            raise FixtureStepError


class FixtureStep(ParsedFlowStep[FixtureStepId, FixtureDraft, str]):
    step_id = FixtureStepId.FIXTURE

    def __init__(self, events: list[str], *, fails: bool = False) -> None:
        super().__init__(
            FixtureDraft,
            FixtureStepParser(events),
            (FixtureStepValidator(events, fails=fails),),
        )
        self._events = events

    def render_validation_error(
        self,
        error: FlowStepError,
        draft: FixtureDraft,
    ) -> TextFlowView:
        self._events.append("render_error")
        return TextFlowView("invalid")

    async def advance(
        self,
        context: FlowContext,
        draft: FixtureDraft,
        value: str,
    ) -> MoveToStep:
        self._events.append("advance")
        return MoveToStep(
            FixtureStepId.NEXT,
            FixtureDraft(value),
            TextFlowView("next"),
        )


async def test_parsed_flow_step_runs_parser_validator_and_transition_in_order() -> None:
    events: list[str] = []
    context = make_flow_context(events, text="answer")

    transition = await FixtureStep(events).handle(context, FixtureDraft("before"))

    assert events == ["parse", "validate", "advance"]
    assert isinstance(transition, MoveToStep)
    assert transition.step_id == FixtureStepId.NEXT
    assert transition.draft == FixtureDraft("answer")


async def test_parsed_flow_step_stays_on_validation_error() -> None:
    events: list[str] = []
    context = make_flow_context(events, text="invalid")

    transition = await FixtureStep(events, fails=True).handle(
        context,
        FixtureDraft("before"),
    )

    assert events == ["parse", "validate", "render_error"]
    assert transition == StayOnStep(TextFlowView("invalid"))


async def test_flow_runner_persists_transition_then_completes_in_order() -> None:
    events: list[str] = []
    command_context, messenger = make_command_context(events)
    flow = FixtureFlow(events)
    runner = FlowRunner(FlowCatalog((flow,)), messenger)

    await runner.start(flow, command_context, "draft")

    assert await command_context.state.get_state() == ActiveFlowState.active.state
    await runner.handle_message(
        make_message("answer"),
        command_context.bot,
        command_context.state,
    )

    assert await command_context.state.get_state() is None
    assert events == [
        "start:draft",
        "reply:started",
        "handle:input",
        "reply:done",
        "post",
    ]


async def test_flow_runner_cancel_delegates_to_active_flow() -> None:
    events: list[str] = []
    command_context, messenger = make_command_context(events)
    flow = FixtureFlow(events)
    runner = FlowRunner(FlowCatalog((flow,)), messenger)
    await runner.start(flow, command_context, "draft")
    events.clear()

    await runner.cancel(command_context)

    assert await command_context.state.get_state() is None
    assert events == ["cancel:input", "reply:cancelled"]


def test_flow_catalog_rejects_duplicate_ids() -> None:
    events: list[str] = []

    with pytest.raises(ValueError, match="Flow ids must be unique"):
        FlowCatalog((FixtureFlow(events), FixtureFlow(events)))


def make_command_context(
    events: list[str],
) -> tuple[CommandContext, RecordingFlowMessenger]:
    flow_context = make_flow_context(events, text="/fixture")
    messenger = RecordingFlowMessenger(events)
    return (
        CommandContext(
            message=flow_context.message,
            bot=flow_context.bot,
            state=flow_context.state,
            profile=flow_context.profile,
            invocation=ParsedCommand("fixture", None, None),
        ),
        messenger,
    )


def make_flow_context(events: list[str], *, text: str) -> FlowContext:
    bot = Bot(token="123456:test-token")
    storage = MemoryStorage()
    state = FSMContext(
        storage=storage,
        key=StorageKey(bot_id=123456, chat_id=42, user_id=42),
    )
    return FlowContext(
        message=make_message(text),
        bot=bot,
        messenger=RecordingFlowMessenger(events),
        state=state,
        profile=TelegramProfile(42, "max", "Max", None),
    )


def make_message(text: str) -> Message:
    return Message(
        message_id=1,
        date=datetime.now(tz=UTC),
        chat=Chat(id=42, type=ChatType.PRIVATE),
        from_user=User(id=42, is_bot=False, first_name="Max"),
        text=text,
    )
