from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from aiogram import Bot
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat, Message, User

from office_food_bot.commands.base import (
    Command,
    CommandContext,
    EffectCommand,
    FlowCommand,
    RawArguments,
    RawArgumentsParser,
    RenderedCommand,
)
from office_food_bot.commands.catalog import CommandCatalog
from office_food_bot.commands.definitions import (
    CommandDefinition,
    CommandScope,
    HelpSection,
)
from office_food_bot.commands.parsing import ParsedCommand
from office_food_bot.messaging import BotMessenger, MessagePayload, TextMessagePayload
from office_food_bot.user_errors import CommonError, CommonErrorCode

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


class RecordingParser:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def parse(self, raw_arguments: str | None) -> RawArguments:
        self._events.append(f"parse:{raw_arguments}")
        return RawArguments(raw_arguments)


class RecordingContextValidator:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def validate(self, context: CommandContext) -> None:
        self._events.append(f"context:{context.invocation.name}")


class RecordingRequestValidator:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def validate(self, context: CommandContext, request: RawArguments) -> None:
        self._events.append(f"request:{request.value}")


class FixtureRenderedCommand(RenderedCommand[RawArguments, str]):
    definition = TEST_DEFINITION

    def __init__(self, events: list[str]) -> None:
        def render(model: str) -> MessagePayload:
            events.append(f"render:{model}")
            return TextMessagePayload(model)

        super().__init__(
            RecordingParser(events),
            (RecordingContextValidator(events),),
            (RecordingRequestValidator(events),),
            render,
        )
        self._events = events

    async def execute(self, context: CommandContext, request: RawArguments) -> str:
        self._events.append(f"execute:{request.value}")
        return "model"


class FixtureEffectCommand(EffectCommand[RawArguments]):
    definition = TEST_DEFINITION

    def __init__(self, events: list[str]) -> None:
        super().__init__(RawArgumentsParser(), (), ())
        self._events = events

    async def execute_effect(
        self,
        context: CommandContext,
        request: RawArguments,
    ) -> None:
        self._events.append(f"effect:{request.value}")


class FixtureFlowCommand(FlowCommand[RawArguments]):
    definition = TEST_DEFINITION

    def __init__(self, events: list[str]) -> None:
        super().__init__(RawArgumentsParser(), (), ())
        self._events = events

    async def start_flow(
        self,
        context: CommandContext,
        request: RawArguments,
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

    def validate(self, context: CommandContext) -> None:
        self._events.append("context:error")
        raise CommonError(CommonErrorCode.ADMIN_REQUIRED)


class FailingFixtureCommand(RenderedCommand[RawArguments, str]):
    definition = TEST_DEFINITION

    def __init__(self, events: list[str]) -> None:
        super().__init__(
            RecordingParser(events),
            (FailingContextValidator(events),),
            (RecordingRequestValidator(events),),
            lambda model: TextMessagePayload(model),
        )

    async def execute(self, context: CommandContext, request: RawArguments) -> str:
        del context, request
        return "unreachable"


class ConcurrentFixtureCommand(RenderedCommand[RawArguments, str]):
    definition = TEST_DEFINITION

    def __init__(self) -> None:
        super().__init__(
            RawArgumentsParser(),
            (),
            (),
            lambda model: TextMessagePayload(model),
        )

    async def execute(self, context: CommandContext, request: RawArguments) -> str:
        del context
        await asyncio.sleep(0)
        return request.value or "empty"


async def test_rendered_command_runs_pipeline_in_order() -> None:
    events: list[str] = []
    command = FixtureRenderedCommand(events)
    context = make_context(command, events, "minutes")

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
    command = FixtureEffectCommand(events)

    await command.handle(make_context(command, events, "15"))

    assert events == ["effect:15"]


async def test_flow_command_delegates_to_flow_start() -> None:
    events: list[str] = []
    command = FixtureFlowCommand(events)

    await command.handle(make_context(command, events, None))

    assert events == ["flow:None"]


def test_command_catalog_resolves_names_and_aliases() -> None:
    events: list[str] = []
    command = AliasedFixtureCommand(events)
    catalog = CommandCatalog((command,))

    assert catalog.resolve("COFFEE") is command
    assert catalog.resolve("КоФе") is command
    assert catalog.invocation_names == ("coffee", "кофе")


def test_command_catalog_rejects_empty_and_duplicate_names() -> None:
    with pytest.raises(ValueError, match="At least one command"):
        CommandCatalog(())

    with pytest.raises(ValueError, match="Duplicate command name or alias"):
        CommandCatalog((FixtureRenderedCommand([]), FixtureRenderedCommand([])))


async def test_pipeline_stops_after_user_facing_error() -> None:
    events: list[str] = []
    command = FailingFixtureCommand(events)

    with pytest.raises(CommonError):
        await command.handle(make_context(command, events, "minutes"))

    assert events == ["context:error"]


async def test_single_command_instance_keeps_parallel_requests_isolated() -> None:
    command = ConcurrentFixtureCommand()
    first_events: list[str] = []
    second_events: list[str] = []
    first_context = make_context(command, first_events, "first")
    second_context = make_context(command, second_events, "second")

    await asyncio.gather(
        command.handle(first_context),
        command.handle(second_context),
    )

    first_messenger = first_context.messenger
    second_messenger = second_context.messenger
    assert isinstance(first_messenger, RecordingMessenger)
    assert isinstance(second_messenger, RecordingMessenger)
    assert payload_texts(first_messenger) == ["first"]
    assert payload_texts(second_messenger) == ["second"]


def make_context(
    command: Command,
    events: list[str],
    arguments: str | None,
) -> CommandContext:
    bot = Bot(token="123456:test-token")
    storage = MemoryStorage()
    state = FSMContext(
        storage=storage,
        key=StorageKey(bot_id=123456, chat_id=42, user_id=42),
    )
    message = Message(
        message_id=1,
        date=datetime.now(tz=UTC),
        chat=Chat(id=42, type=ChatType.PRIVATE),
        from_user=User(id=42, is_bot=False, first_name="Max"),
        text="/test",
    )
    catalog = CommandCatalog((command,))
    return CommandContext(
        message=message,
        bot=bot,
        messenger=RecordingMessenger(events),
        state=state,
        profile=None,
        invocation=ParsedCommand("test", arguments, None),
        catalog=catalog,
    )


def payload_texts(messenger: RecordingMessenger) -> list[str]:
    assert all(isinstance(payload, TextMessagePayload) for payload in messenger.payloads)
    return [
        payload.text for payload in messenger.payloads if isinstance(payload, TextMessagePayload)
    ]
