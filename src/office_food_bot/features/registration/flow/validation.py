from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from aiogram.types import Message

from office_food_bot.boolean_input import parse_confirmation
from office_food_bot.features.registration.flow.draft import RegistrationDraft
from office_food_bot.flows.contracts import FlowContext
from office_food_bot.result import Result, failure, success

SPLITWISE_SKIP_ANSWERS = frozenset({"пропустить", "skip"})


class RegistrationStepErrorCode(StrEnum):
    NAME_TEXT_REQUIRED = "name_text_required"
    NAME_EMPTY = "name_empty"
    SPLITWISE_TEXT_REQUIRED = "splitwise_text_required"
    LUNCH_CHOICE_REQUIRED = "lunch_choice_required"
    COFFEE_CHOICE_REQUIRED = "coffee_choice_required"
    REREGISTRATION_CHOICE_REQUIRED = "reregistration_choice_required"


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
    ) -> Result[None, RegistrationStepErrorCode]:
        if value.text is None:
            return failure(RegistrationStepErrorCode.NAME_TEXT_REQUIRED)
        if not value.text.strip():
            return failure(RegistrationStepErrorCode.NAME_EMPTY)
        return success(None)


class SplitwiseAnswerValidator:
    def validate(
        self,
        context: FlowContext,
        draft: RegistrationDraft,
        value: TextFlowInput,
    ) -> Result[None, RegistrationStepErrorCode]:
        if value.text is None or not value.text.strip():
            return failure(RegistrationStepErrorCode.SPLITWISE_TEXT_REQUIRED)
        return success(None)


class LunchPreferenceValidator:
    def validate(
        self,
        context: FlowContext,
        draft: RegistrationDraft,
        value: TextFlowInput,
    ) -> Result[None, RegistrationStepErrorCode]:
        return _validate_confirmation(
            value,
            RegistrationStepErrorCode.LUNCH_CHOICE_REQUIRED,
        )


class CoffeePreferenceValidator:
    def validate(
        self,
        context: FlowContext,
        draft: RegistrationDraft,
        value: TextFlowInput,
    ) -> Result[None, RegistrationStepErrorCode]:
        return _validate_confirmation(
            value,
            RegistrationStepErrorCode.COFFEE_CHOICE_REQUIRED,
        )


class ReregistrationDecisionValidator:
    def validate(
        self,
        context: FlowContext,
        draft: RegistrationDraft,
        value: TextFlowInput,
    ) -> Result[None, RegistrationStepErrorCode]:
        return _validate_confirmation(
            value,
            RegistrationStepErrorCode.REREGISTRATION_CHOICE_REQUIRED,
        )


def is_splitwise_skip(value: TextFlowInput) -> bool:
    return _normalized(value) in SPLITWISE_SKIP_ANSWERS


def confirmation_value(value: TextFlowInput) -> bool:
    confirmed = parse_confirmation(value.text or "")
    if confirmed is None:
        raise RuntimeError("Confirmation input was not validated")
    return confirmed


def required_text(value: TextFlowInput) -> str:
    if value.text is None or not value.text.strip():
        raise RuntimeError("Text input was not validated")
    return value.text


def _validate_confirmation(
    value: TextFlowInput,
    error_code: RegistrationStepErrorCode,
) -> Result[None, RegistrationStepErrorCode]:
    if parse_confirmation(value.text or "") is None:
        return failure(error_code)
    return success(None)


def _normalized(value: TextFlowInput) -> str:
    return (value.text or "").strip().casefold()
