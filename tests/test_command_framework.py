from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from aiogram import Bot
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat, Message, User

from office_food_bot.commanding.catalog import CommandCatalog
from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
    FlowCommand,
    RenderedCommand,
)
from office_food_bot.commanding.definition import (
    CommandDefinition,
    CommandScope,
    HelpSection,
)
from office_food_bot.commanding.errors.models import CommonErrorCode, InputErrorCode
from office_food_bot.commanding.errors.rendering import CommonErrorRenderer
from office_food_bot.commanding.invocation import ParsedCommand
from office_food_bot.messaging import BotMessenger, MessagePayload, TextMessagePayload
from office_food_bot.result import Result, failure, success

TEST_DEFINITION = CommandDefinition(
    "test",
    "test command",
    "/test",
    CommandScope.ANY,
    HelpSection.SERVICE,
)


class RecordingMessenger(BotMessenger):
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.payloads: list[MessagePayload] = []

    async def reply_payload(
        self,
        message: Message,
        payload: MessagePayload,
    ) -> Message:
        self.events.append("reply")
        self.payloads.append(payload)
        return message


@dataclass(frozen=True, slots=True)
class FixtureRequest:
    value: str | None


class RecordingParser:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def parse(
        self,
        raw_arguments: str | None,
    ) -> Result[FixtureRequest, InputErrorCode]:
        self._events.append(f"parse:{raw_arguments}")
        return success(FixtureRequest(raw_arguments))


class FixtureParser:
    def parse(
        self,
        raw_arguments: str | None,
    ) -> Result[FixtureRequest, InputErrorCode]:
        return success(FixtureRequest(raw_arguments))


class RecordingContextValidator:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def validate(
        self,
        context: CommandContext,
    ) -> Result[None, CommonErrorCode]:
        self._events.append(f"context:{context.invocation.name}")
        return success(None)


class RecordingRequestValidator:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def validate(
        self,
        context: CommandContext,
        request: FixtureRequest,
    ) -> Result[None, CommonErrorCode]:
        self._events.append(f"request:{request.value}")
        return success(None)


class FixtureRenderedCommand(RenderedCommand[FixtureRequest, str]):
    definition = TEST_DEFINITION

    def __init__(self, messenger: BotMessenger, events: list[str]) -> None:
        def render(model: str) -> MessagePayload:
            events.append(f"render:{model}")
            return TextMessagePayload(model)

        super().__init__(
            messenger,
            CommonErrorRenderer("foodbot_dev"),
            RecordingParser(events),
            (RecordingContextValidator(events),),
            (RecordingRequestValidator(events),),
            render,
        )
        self._events = events

    async def execute(self, context: CommandContext, request: FixtureRequest) -> str:
        self._events.append(f"execute:{request.value}")
        return "model"


class FixtureEffectCommand(EffectCommand[FixtureRequest]):
    definition = TEST_DEFINITION

    def __init__(self, messenger: BotMessenger, events: list[str]) -> None:
        super().__init__(
            messenger,
            CommonErrorRenderer("foodbot_dev"),
            FixtureParser(),
            (),
            (),
        )
        self._events = events

    async def execute_effect(
        self,
        context: CommandContext,
        request: FixtureRequest,
    ) -> None:
        self._events.append(f"effect:{request.value}")


class FixtureFlowCommand(FlowCommand[FixtureRequest]):
    definition = TEST_DEFINITION

    def __init__(self, messenger: BotMessenger, events: list[str]) -> None:
        super().__init__(
            messenger,
            CommonErrorRenderer("foodbot_dev"),
            FixtureParser(),
            (),
            (),
        )
        self._events = events

    async def start_flow(
        self,
        context: CommandContext,
        request: FixtureRequest,
    ) -> None:
        self._events.append(f"flow:{request.value}")


class AliasedFixtureCommand(FixtureRenderedCommand):
    definition = CommandDefinition(
        "coffee",
        "coffee",
        "/coffee",
        CommandScope.ANY,
        HelpSection.MAIN,
        text_aliases=("кофе",),
    )


class FailingContextValidator:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def validate(
        self,
        context: CommandContext,
    ) -> Result[None, CommonErrorCode]:
        self._events.append("context:error")
        return failure(CommonErrorCode.ADMIN_REQUIRED)


class FailingFixtureCommand(RenderedCommand[FixtureRequest, str]):
    definition = TEST_DEFINITION

    def __init__(self, messenger: BotMessenger, events: list[str]) -> None:
        super().__init__(
            messenger,
            CommonErrorRenderer("foodbot_dev"),
            RecordingParser(events),
            (FailingContextValidator(events),),
            (RecordingRequestValidator(events),),
            lambda model: TextMessagePayload(model),
        )

    async def execute(self, context: CommandContext, request: FixtureRequest) -> str:
        del context, request
        return "unreachable"


class ConcurrentFixtureCommand(RenderedCommand[FixtureRequest, str]):
    definition = TEST_DEFINITION

    def __init__(self, messenger: BotMessenger) -> None:
        super().__init__(
            messenger,
            CommonErrorRenderer("foodbot_dev"),
            FixtureParser(),
            (),
            (),
            lambda model: TextMessagePayload(model),
        )

    async def execute(self, context: CommandContext, request: FixtureRequest) -> str:
        del context
        await asyncio.sleep(0)
        return request.value or "empty"


async def test_rendered_command_runs_pipeline_in_order() -> None:
    events: list[str] = []
    messenger = RecordingMessenger(events)
    command = FixtureRenderedCommand(messenger, events)
    context = make_context("minutes")

    await command.handle(context)

    assert events == [
        "context:test",
        "parse:minutes",
        "request:minutes",
        "execute:minutes",
        "render:model",
        "reply",
    ]


async def test_effect_command_does_not_send_automatic_reply() -> None:
    events: list[str] = []
    command = FixtureEffectCommand(RecordingMessenger(events), events)

    await command.handle(make_context("15"))

    assert events == ["effect:15"]


async def test_flow_command_delegates_to_flow_start() -> None:
    events: list[str] = []
    command = FixtureFlowCommand(RecordingMessenger(events), events)

    await command.handle(make_context(None))

    assert events == ["flow:None"]


def test_command_catalog_resolves_names_and_aliases() -> None:
    events: list[str] = []
    command = AliasedFixtureCommand(RecordingMessenger(events), events)
    catalog = CommandCatalog((command,))

    assert catalog.resolve("COFFEE") is command
    assert catalog.resolve("КоФе") is command
    assert catalog.invocation_names == ("coffee", "кофе")


def test_command_catalog_rejects_empty_and_duplicate_names() -> None:
    with pytest.raises(ValueError, match="At least one command"):
        CommandCatalog(())

    with pytest.raises(ValueError, match="Duplicate command name or alias"):
        first_events: list[str] = []
        second_events: list[str] = []
        CommandCatalog(
            (
                FixtureRenderedCommand(RecordingMessenger(first_events), first_events),
                FixtureRenderedCommand(RecordingMessenger(second_events), second_events),
            )
        )


async def test_pipeline_stops_after_user_facing_error() -> None:
    events: list[str] = []
    messenger = RecordingMessenger(events)
    command = FailingFixtureCommand(messenger, events)

    await command.handle(make_context("minutes"))

    assert events == ["context:error", "reply"]
    assert payload_texts(messenger) == ["Команда доступна только админам."]


async def test_single_command_instance_keeps_parallel_requests_isolated() -> None:
    events: list[str] = []
    messenger = RecordingMessenger(events)
    command = ConcurrentFixtureCommand(messenger)
    first_context = make_context("first", chat_id=41)
    second_context = make_context("second", chat_id=42)

    await asyncio.gather(
        command.handle(first_context),
        command.handle(second_context),
    )

    assert sorted(payload_texts(messenger)) == ["first", "second"]


def make_context(arguments: str | None, *, chat_id: int = 42) -> CommandContext:
    bot = Bot(token="123456:test-token")
    storage = MemoryStorage()
    state = FSMContext(
        storage=storage,
        key=StorageKey(bot_id=123456, chat_id=chat_id, user_id=42),
    )
    message = Message(
        message_id=1,
        date=datetime.now(tz=UTC),
        chat=Chat(id=chat_id, type=ChatType.PRIVATE),
        from_user=User(id=42, is_bot=False, first_name="Max"),
        text="/test",
    )
    return CommandContext(
        message=message,
        bot=bot,
        state=state,
        profile=None,
        invocation=ParsedCommand("test", arguments, None),
    )


def payload_texts(messenger: RecordingMessenger) -> list[str]:
    assert all(isinstance(payload, TextMessagePayload) for payload in messenger.payloads)
    return [
        payload.text for payload in messenger.payloads if isinstance(payload, TextMessagePayload)
    ]
