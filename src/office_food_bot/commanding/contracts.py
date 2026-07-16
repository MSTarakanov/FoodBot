from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, final

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from office_food_bot.commanding.definition import CommandDefinition
from office_food_bot.commanding.errors.models import CommonErrorCode, InputErrorCode
from office_food_bot.commanding.errors.rendering import (
    CommandInputErrorRenderer,
    ErrorRenderer,
)
from office_food_bot.commanding.invocation import ParsedCommand
from office_food_bot.messaging import BotMessenger, MessagePayload, TextMessagePayload
from office_food_bot.models import TelegramProfile
from office_food_bot.result import Result, success


@dataclass(frozen=True, slots=True)
class CommandContext:
    message: Message
    bot: Bot
    state: FSMContext
    profile: TelegramProfile | None
    invocation: ParsedCommand


class Parser[RequestT](Protocol):
    def parse(
        self,
        raw_arguments: str | None,
    ) -> Result[RequestT, InputErrorCode]: ...


class ContextValidator(Protocol):
    def validate(
        self,
        context: CommandContext,
    ) -> Result[None, CommonErrorCode]: ...


class Validator[RequestT](Protocol):
    def validate(
        self,
        context: CommandContext,
        request: RequestT,
    ) -> Result[None, CommonErrorCode]: ...


class Renderer[ModelT](Protocol):
    def __call__(self, model: ModelT, /) -> MessagePayload: ...


class Command(Protocol):
    definition: CommandDefinition

    async def handle(self, context: CommandContext) -> None: ...


class ParsedRequestCommand[RequestT](ABC):
    definition: CommandDefinition

    def __init__(
        self,
        messenger: BotMessenger,
        common_error_renderer: ErrorRenderer[CommonErrorCode],
        parser: Parser[RequestT],
        context_validators: tuple[ContextValidator, ...],
        validators: tuple[Validator[RequestT], ...],
    ) -> None:
        self._messenger = messenger
        self._common_error_renderer = common_error_renderer
        self._input_error_renderer = CommandInputErrorRenderer(self.definition)
        self._parser = parser
        self._context_validators = context_validators
        self._validators = validators

    @final
    async def handle(self, context: CommandContext) -> None:
        await self._validated_request(context).fold(
            lambda request: self._handle_validated(context, request),
            lambda text: self._reply_error(context, text),
        )

    def _validated_request(self, context: CommandContext) -> Result[RequestT, str]:
        context_validation = _validate_context(
            context,
            self._context_validators,
        ).map_error(self._common_error_renderer.render)
        parsed_request = context_validation.and_then(
            lambda _: self._parser.parse(
                context.invocation.arguments
            ).map_error(self._input_error_renderer.render)
        )
        return parsed_request.and_then(
            lambda request: _validate_request(
                context,
                request,
                self._validators,
            )
            .map_error(self._common_error_renderer.render)
            .map(lambda _: request)
        )

    async def _reply_error(self, context: CommandContext, text: str) -> None:
        await self._messenger.reply_payload(
            context.message,
            TextMessagePayload(text),
        )

    async def _reply_common_error(
        self,
        context: CommandContext,
        code: CommonErrorCode,
    ) -> None:
        await self._reply_error(context, self._common_error_renderer.render(code))

    @abstractmethod
    async def _handle_validated(
        self,
        context: CommandContext,
        request: RequestT,
    ) -> None: ...


class RenderedCommand[RequestT, ModelT](ParsedRequestCommand[RequestT], ABC):
    def __init__(
        self,
        messenger: BotMessenger,
        common_error_renderer: ErrorRenderer[CommonErrorCode],
        parser: Parser[RequestT],
        context_validators: tuple[ContextValidator, ...],
        validators: tuple[Validator[RequestT], ...],
        renderer: Renderer[ModelT],
    ) -> None:
        super().__init__(
            messenger,
            common_error_renderer,
            parser,
            context_validators,
            validators,
        )
        self._renderer = renderer

    @final
    async def _handle_validated(
        self,
        context: CommandContext,
        request: RequestT,
    ) -> None:
        model = await self.execute(context, request)
        await self._messenger.reply_payload(
            context.message,
            self._renderer(model),
        )

    @abstractmethod
    async def execute(self, context: CommandContext, request: RequestT) -> ModelT: ...


class ResultRenderedCommand[RequestT, ModelT, ErrorT](
    ParsedRequestCommand[RequestT],
    ABC,
):
    def __init__(
        self,
        messenger: BotMessenger,
        common_error_renderer: ErrorRenderer[CommonErrorCode],
        parser: Parser[RequestT],
        context_validators: tuple[ContextValidator, ...],
        validators: tuple[Validator[RequestT], ...],
        renderer: Renderer[ModelT],
        error_renderer: ErrorRenderer[ErrorT],
    ) -> None:
        super().__init__(
            messenger,
            common_error_renderer,
            parser,
            context_validators,
            validators,
        )
        self._renderer = renderer
        self._error_renderer = error_renderer

    @final
    async def _handle_validated(
        self,
        context: CommandContext,
        request: RequestT,
    ) -> None:
        result = await self.execute(context, request)
        payload = result.fold(
            self._renderer,
            lambda error: TextMessagePayload(self._error_renderer.render(error)),
        )
        await self._messenger.reply_payload(context.message, payload)

    @abstractmethod
    async def execute(
        self,
        context: CommandContext,
        request: RequestT,
    ) -> Result[ModelT, ErrorT]: ...


class EffectCommand[RequestT](ParsedRequestCommand[RequestT], ABC):
    @final
    async def _handle_validated(
        self,
        context: CommandContext,
        request: RequestT,
    ) -> None:
        await self.execute_effect(context, request)

    @abstractmethod
    async def execute_effect(self, context: CommandContext, request: RequestT) -> None: ...


class FlowCommand[RequestT](ParsedRequestCommand[RequestT], ABC):
    @final
    async def _handle_validated(
        self,
        context: CommandContext,
        request: RequestT,
    ) -> None:
        await self.start_flow(context, request)

    @abstractmethod
    async def start_flow(self, context: CommandContext, request: RequestT) -> None: ...


@dataclass(frozen=True, slots=True)
class NoArguments:
    pass


class NoArgumentsParser:
    def parse(
        self,
        raw_arguments: str | None,
    ) -> Result[NoArguments, InputErrorCode]:
        return success(NoArguments())


def _validate_context(
    context: CommandContext,
    validators: tuple[ContextValidator, ...],
) -> Result[None, CommonErrorCode]:
    result: Result[None, CommonErrorCode] = success(None)
    for validator in validators:

        def validate_next(
            _: None,
            current: ContextValidator = validator,
        ) -> Result[None, CommonErrorCode]:
            return current.validate(context)

        result = result.and_then(validate_next)
    return result


def _validate_request[RequestT](
    context: CommandContext,
    request: RequestT,
    validators: tuple[Validator[RequestT], ...],
) -> Result[None, CommonErrorCode]:
    result: Result[None, CommonErrorCode] = success(None)
    for validator in validators:

        def validate_next(
            _: None,
            current: Validator[RequestT] = validator,
        ) -> Result[None, CommonErrorCode]:
            return current.validate(context, request)

        result = result.and_then(validate_next)
    return result
