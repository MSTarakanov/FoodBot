from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    ContextValidator,
    FlowCommand,
    Parser,
    Validator,
)
from office_food_bot.commanding.definition import (
    CommandDefinition,
    CommandInputMessage,
    CommandScope,
    HelpSection,
)
from office_food_bot.commanding.errors.models import InputErrorCode
from office_food_bot.flows.registration.flow import RegistrationFlow
from office_food_bot.flows.registration.requests import RegisterRequest
from office_food_bot.flows.runner import FlowRunner
from office_food_bot.messaging import BotMessenger


class RegisterCommand(FlowCommand[RegisterRequest]):
    definition = CommandDefinition(
        "register",
        "пройти регистрацию",
        "/register",
        CommandScope.PRIVATE,
        HelpSection.PROFILE_SETTINGS,
        input_errors=(
            CommandInputMessage(
                InputErrorCode.INVALID_FORMAT,
                "Telegram ID должен быть числом: /register 123456789",
            ),
        ),
    )

    def __init__(
        self,
        messenger: BotMessenger,
        parser: Parser[RegisterRequest],
        context_validators: tuple[ContextValidator, ...],
        validators: tuple[Validator[RegisterRequest], ...],
        runner: FlowRunner,
        flow: RegistrationFlow,
    ) -> None:
        super().__init__(messenger, parser, context_validators, validators)
        self._runner = runner
        self._flow = flow

    async def start_flow(
        self,
        context: CommandContext,
        request: RegisterRequest,
    ) -> None:
        await self._runner.start(self._flow, context, request)
