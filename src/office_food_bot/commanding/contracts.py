from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, final

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commanding.definition import CommandDefinition
from office_food_bot.commanding.invocation import ParsedCommand
from office_food_bot.messaging import BotMessenger, MessagePayload
from office_food_bot.models import TelegramProfile

if TYPE_CHECKING:
    from office_food_bot.commanding.catalog import CommandCatalog


@dataclass(frozen=True, slots=True)
class CommandContext:
    message: Message
    bot: Bot
    messenger: BotMessenger
    state: FSMContext
    profile: TelegramProfile | None
    invocation: ParsedCommand
    catalog: CommandCatalog


class Parser[RequestT](Protocol):
    def parse(self, raw_arguments: str | None) -> RequestT: ...


class ContextValidator(Protocol):
    def validate(self, context: CommandContext) -> None: ...


class Validator[RequestT](Protocol):
    def validate(self, context: CommandContext, request: RequestT) -> None: ...


class Renderer[ModelT](Protocol):
    def __call__(self, model: ModelT, /) -> MessagePayload: ...


class Command(ABC):
    definition: CommandDefinition

    @abstractmethod
    async def handle(self, context: CommandContext) -> None: ...


class ParsedRequestCommand[RequestT](Command, ABC):
    def __init__(
        self,
        parser: Parser[RequestT],
        context_validators: tuple[ContextValidator, ...],
        validators: tuple[Validator[RequestT], ...],
    ) -> None:
        self._parser = parser
        self._context_validators = context_validators
        self._validators = validators

    def _validated_request(self, context: CommandContext) -> RequestT:
        for context_validator in self._context_validators:
            context_validator.validate(context)
        request = self._parser.parse(context.invocation.arguments)
        for request_validator in self._validators:
            request_validator.validate(context, request)
        return request


class RenderedCommand[RequestT, ModelT](ParsedRequestCommand[RequestT], ABC):
    def __init__(
        self,
        parser: Parser[RequestT],
        context_validators: tuple[ContextValidator, ...],
        validators: tuple[Validator[RequestT], ...],
        renderer: Renderer[ModelT],
    ) -> None:
        super().__init__(parser, context_validators, validators)
        self._renderer = renderer

    @final
    async def handle(self, context: CommandContext) -> None:
        request = self._validated_request(context)
        model = await self.execute(context, request)
        await context.messenger.reply_payload(
            context.message,
            self._renderer(model),
        )

    @abstractmethod
    async def execute(self, context: CommandContext, request: RequestT) -> ModelT: ...


class EffectCommand[RequestT](ParsedRequestCommand[RequestT], ABC):
    @final
    async def handle(self, context: CommandContext) -> None:
        request = self._validated_request(context)
        await self.execute_effect(context, request)

    @abstractmethod
    async def execute_effect(self, context: CommandContext, request: RequestT) -> None: ...


class FlowCommand[RequestT](ParsedRequestCommand[RequestT], ABC):
    @final
    async def handle(self, context: CommandContext) -> None:
        request = self._validated_request(context)
        await self.start_flow(context, request)

    @abstractmethod
    async def start_flow(self, context: CommandContext, request: RequestT) -> None: ...


@dataclass(frozen=True, slots=True)
class RawArguments:
    value: str | None


class RawArgumentsParser:
    def parse(self, raw_arguments: str | None) -> RawArguments:
        return RawArguments(raw_arguments)
