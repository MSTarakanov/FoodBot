from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from office_food_bot.commands.definitions import CommandDefinition
from office_food_bot.user_errors import (
    BalanceError,
    BalanceErrorCode,
    CommandInputError,
    CommonError,
    CommonErrorCode,
    CommonUserError,
    ExternalDependency,
    InfrastructureUnavailableError,
    UserFacingError,
)


@dataclass(frozen=True, slots=True)
class ErrorRenderContext:
    bot_username: str
    definition: CommandDefinition | None


type ErrorRenderFunction = Callable[[UserFacingError, ErrorRenderContext], str]


@dataclass(frozen=True, slots=True)
class ErrorRendererRegistration:
    error_type: type[UserFacingError]
    render: ErrorRenderFunction


class UserErrorRenderer:
    def __init__(self, registrations: Iterable[ErrorRendererRegistration]) -> None:
        registration_list = tuple(registrations)
        if not registration_list:
            raise ValueError("At least one error renderer must be registered")
        error_types = tuple(registration.error_type for registration in registration_list)
        if len(set(error_types)) != len(error_types):
            raise ValueError("Error renderer types must be unique")
        self._registrations = registration_list

    def render(self, error: UserFacingError, context: ErrorRenderContext) -> str:
        matches = tuple(
            registration
            for registration in self._registrations
            if isinstance(error, registration.error_type)
        )
        if len(matches) != 1:
            raise RuntimeError(
                f"Expected one renderer for {type(error).__name__}, found {len(matches)}"
            )
        return matches[0].render(error, context)


class CommonErrorRenderer:
    def __call__(self, error: UserFacingError, context: ErrorRenderContext) -> str:
        if isinstance(error, CommonError):
            return self._common_error_text(error.code, context)
        if isinstance(error, CommandInputError):
            definition = context.definition
            if definition is None:
                raise RuntimeError("Command input error has no command definition")
            return definition.input_error_text(error.code)
        if isinstance(error, InfrastructureUnavailableError):
            if error.dependency == ExternalDependency.SPLITWISE:
                return "Не смог получить балансы Splitwise. Попробуй позже."
            return "Не смог получить данные внешнего сервиса. Попробуй позже."
        raise TypeError(f"Unsupported common error: {type(error).__name__}")

    def _common_error_text(
        self,
        code: CommonErrorCode,
        context: ErrorRenderContext,
    ) -> str:
        if code == CommonErrorCode.MISSING_TELEGRAM_IDENTITY:
            return "Не вижу твой Telegram user id."
        if code == CommonErrorCode.PRIVATE_CHAT_REQUIRED:
            return f"Команда доступна только в личке: https://t.me/{context.bot_username}"
        if code == CommonErrorCode.GROUP_CHAT_REQUIRED:
            return "Команда доступна только в групповом чате."
        if code == CommonErrorCode.ADMIN_REQUIRED:
            return "Команда доступна только админам."
        if code == CommonErrorCode.REGISTRATION_REQUIRED:
            return "Сначала зарегистрируйся: /register"
        if code == CommonErrorCode.REGISTRATION_PENDING:
            return "Регистрация еще ждет аппрува."
        if code == CommonErrorCode.REGISTRATION_INACTIVE:
            return "Регистрация сейчас неактивна."
        if code == CommonErrorCode.INTERNAL:
            return "Произошла ошибка. Попробуй позже."
        raise ValueError(f"Unsupported common error code: {code}")


def render_balance_error(error: UserFacingError, context: ErrorRenderContext) -> str:
    if not isinstance(error, BalanceError):
        raise TypeError(f"Unsupported balance error: {type(error).__name__}")
    if error.code == BalanceErrorCode.NO_SPLITWISE_USERS:
        return "Splitwise пока не подключен."
    raise ValueError(f"Unsupported balance error code: {error.code}")


def build_user_error_renderer() -> UserErrorRenderer:
    common_renderer = CommonErrorRenderer()
    return UserErrorRenderer(
        (
            ErrorRendererRegistration(CommonUserError, common_renderer),
            ErrorRendererRegistration(BalanceError, render_balance_error),
        )
    )
