from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from aiogram.types import Message

from office_food_bot.flows.contracts import FlowContext, FlowStepError
from office_food_bot.flows.registration.draft import RegistrationDraft

SPLITWISE_SKIP_ANSWERS = frozenset({"пропустить", "skip"})
YES_ANSWERS = frozenset({"да", "yes", "y"})
NO_ANSWERS = frozenset({"нет", "no", "n"})


class RegistrationStepErrorCode(StrEnum):
    NAME_TEXT_REQUIRED = "name_text_required"
    NAME_EMPTY = "name_empty"
    SPLITWISE_TEXT_REQUIRED = "splitwise_text_required"
    LUNCH_CHOICE_REQUIRED = "lunch_choice_required"
    COFFEE_CHOICE_REQUIRED = "coffee_choice_required"
    REREGISTRATION_CHOICE_REQUIRED = "reregistration_choice_required"


class RegistrationStepError(FlowStepError):
    def __init__(self, code: RegistrationStepErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


@dataclass(frozen=True, slots=True)
class TextFlowInput:
    text: str | None


class TextFlowInputParser:
    def parse(self, message: Message) -> TextFlowInput:
        return TextFlowInput(message.text)


class RegistrationNameValidator:
    def validate(
        self,
        context: FlowContext,
        draft: RegistrationDraft,
        value: TextFlowInput,
    ) -> None:
        if value.text is None:
            raise RegistrationStepError(RegistrationStepErrorCode.NAME_TEXT_REQUIRED)
        if not value.text.strip():
            raise RegistrationStepError(RegistrationStepErrorCode.NAME_EMPTY)


class SplitwiseAnswerValidator:
    def validate(
        self,
        context: FlowContext,
        draft: RegistrationDraft,
        value: TextFlowInput,
    ) -> None:
        if value.text is None or not value.text.strip():
            raise RegistrationStepError(RegistrationStepErrorCode.SPLITWISE_TEXT_REQUIRED)


class LunchPreferenceValidator:
    def validate(
        self,
        context: FlowContext,
        draft: RegistrationDraft,
        value: TextFlowInput,
    ) -> None:
        _validate_yes_no(value, RegistrationStepErrorCode.LUNCH_CHOICE_REQUIRED)


class CoffeePreferenceValidator:
    def validate(
        self,
        context: FlowContext,
        draft: RegistrationDraft,
        value: TextFlowInput,
    ) -> None:
        _validate_yes_no(value, RegistrationStepErrorCode.COFFEE_CHOICE_REQUIRED)


class ReregistrationDecisionValidator:
    def validate(
        self,
        context: FlowContext,
        draft: RegistrationDraft,
        value: TextFlowInput,
    ) -> None:
        _validate_yes_no(
            value,
            RegistrationStepErrorCode.REREGISTRATION_CHOICE_REQUIRED,
        )


def is_splitwise_skip(value: TextFlowInput) -> bool:
    return _normalized(value) in SPLITWISE_SKIP_ANSWERS


def yes_no_value(value: TextFlowInput) -> bool:
    normalized = _normalized(value)
    if normalized in YES_ANSWERS:
        return True
    if normalized in NO_ANSWERS:
        return False
    raise RuntimeError("Yes/no input was not validated")


def required_text(value: TextFlowInput) -> str:
    if value.text is None or not value.text.strip():
        raise RuntimeError("Text input was not validated")
    return value.text


def _validate_yes_no(
    value: TextFlowInput,
    error_code: RegistrationStepErrorCode,
) -> None:
    normalized = _normalized(value)
    if normalized not in YES_ANSWERS and normalized not in NO_ANSWERS:
        raise RegistrationStepError(error_code)


def _normalized(value: TextFlowInput) -> str:
    return (value.text or "").strip().casefold()
