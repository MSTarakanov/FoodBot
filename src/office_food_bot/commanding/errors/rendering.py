from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass

from office_food_bot.commanding.definition import CommandDefinition
from office_food_bot.commanding.errors.models import (
    BalanceError,
    BalanceErrorCode,
    CoffeeError,
    CoffeeErrorCode,
    CommandInputError,
    CommonError,
    CommonErrorCode,
    CommonUserError,
    ExternalDependency,
    InfrastructureUnavailableError,
    RegistrationError,
    RegistrationErrorCode,
    UserFacingError,
)


class ErrorRenderer(ABC):
    @abstractmethod
    def render(self, error: UserFacingError) -> str: ...


class DelegatingErrorRenderer(ErrorRenderer):
    def __init__(self, base: ErrorRenderer) -> None:
        self._base = base

    def render(self, error: UserFacingError) -> str:
        return self._base.render(error)


@dataclass(frozen=True, slots=True)
class ErrorRendererRegistration:
    error_type: type[UserFacingError]
    renderer: ErrorRenderer


class UserErrorRenderer(ErrorRenderer):
    def __init__(self, registrations: Iterable[ErrorRendererRegistration]) -> None:
        registration_list = tuple(registrations)
        if not registration_list:
            raise ValueError("At least one error renderer must be registered")
        error_types = tuple(registration.error_type for registration in registration_list)
        if len(set(error_types)) != len(error_types):
            raise ValueError("Error renderer types must be unique")
        self._registrations = registration_list

    def render(self, error: UserFacingError) -> str:
        matches = tuple(
            registration
            for registration in self._registrations
            if isinstance(error, registration.error_type)
        )
        if len(matches) != 1:
            raise RuntimeError(
                f"Expected one renderer for {type(error).__name__}, found {len(matches)}"
            )
        return matches[0].renderer.render(error)


class CommandErrorRenderer(DelegatingErrorRenderer):
    def __init__(self, base: ErrorRenderer, definition: CommandDefinition) -> None:
        super().__init__(base)
        self._definition = definition

    def render(self, error: UserFacingError) -> str:
        if isinstance(error, CommandInputError):
            return self._definition.input_error_text(error.code)
        return super().render(error)


class BotUsernameErrorRenderer(DelegatingErrorRenderer):
    def __init__(self, base: ErrorRenderer, bot_username: str) -> None:
        super().__init__(base)
        self._bot_username = bot_username

    def render(self, error: UserFacingError) -> str:
        if (
            isinstance(error, CommonError)
            and error.code == CommonErrorCode.PRIVATE_CHAT_REQUIRED
        ):
            return (
                "Команда доступна только в личке: "
                f"https://t.me/{self._bot_username}"
            )
        return super().render(error)


class CallbackErrorRenderer(DelegatingErrorRenderer):
    def render(self, error: UserFacingError) -> str:
        if (
            isinstance(error, CommonError)
            and error.code == CommonErrorCode.REGISTRATION_REQUIRED
        ):
            return (
                "Чтобы пользоваться этой функцией, сначала зарегистрируйся.\n"
                "В личном чате с ботом запусти /register и пройди регистрацию сам "
                "или отправь /request_register, чтобы тебя зарегистрировал "
                "администратор."
            )
        return super().render(error)


class CommonErrorRenderer(ErrorRenderer):
    def render(self, error: UserFacingError) -> str:
        if isinstance(error, CommandInputError):
            raise RuntimeError("Command input error requires CommandErrorRenderer")
        if isinstance(error, CommonError):
            return self._common_error_text(error.code)
        if isinstance(error, InfrastructureUnavailableError):
            if error.dependency == ExternalDependency.SPLITWISE:
                return "Не смог получить балансы Splitwise. Попробуй позже."
            return "Не смог получить данные внешнего сервиса. Попробуй позже."
        raise TypeError(f"Unsupported common error: {type(error).__name__}")

    def _common_error_text(self, code: CommonErrorCode) -> str:
        if code == CommonErrorCode.MISSING_TELEGRAM_IDENTITY:
            return "Не вижу твой Telegram user id."
        if code == CommonErrorCode.PRIVATE_CHAT_REQUIRED:
            raise RuntimeError("Private chat error requires BotUsernameErrorRenderer")
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


class BalanceErrorRenderer(ErrorRenderer):
    def render(self, error: UserFacingError) -> str:
        if not isinstance(error, BalanceError):
            raise TypeError(f"Unsupported balance error: {type(error).__name__}")
        if error.code == BalanceErrorCode.NO_SPLITWISE_USERS:
            return "Splitwise пока не подключен."
        raise ValueError(f"Unsupported balance error code: {error.code}")


class CoffeeErrorRenderer(ErrorRenderer):
    def render(self, error: UserFacingError) -> str:
        if not isinstance(error, CoffeeError):
            raise TypeError(f"Unsupported coffee error: {type(error).__name__}")
        if error.code == CoffeeErrorCode.INVALID_CALLBACK:
            return "Не понял действие."
        if error.code == CoffeeErrorCode.SESSION_ENDED:
            return "Эта встреча уже завершена."
        raise ValueError(f"Unsupported coffee error code: {error.code}")


class RegistrationErrorRenderer(ErrorRenderer):
    def render(self, error: UserFacingError) -> str:
        if not isinstance(error, RegistrationError):
            raise TypeError(f"Unsupported registration error: {type(error).__name__}")
        if error.code == RegistrationErrorCode.REQUEST_ALREADY_PENDING:
            return (
                "Заявка уже ждет аппрува. "
                "Если хотите отменить регистрацию, отправьте /quit."
            )
        if error.code == RegistrationErrorCode.REQUEST_ALREADY_ACTIVE:
            return (
                "Вы уже зарегистрированы. "
                "Если хотите отрегистрироваться, отправьте /quit."
            )
        if error.code == RegistrationErrorCode.REQUEST_UNAVAILABLE:
            return (
                "Регистрация сейчас недоступна. "
                "Если хотите отрегистрироваться, отправьте /quit."
            )
        raise ValueError(f"Unsupported registration error code: {error.code}")


def build_user_error_renderer() -> UserErrorRenderer:
    return UserErrorRenderer(
        (
            ErrorRendererRegistration(CommonUserError, CommonErrorRenderer()),
            ErrorRendererRegistration(BalanceError, BalanceErrorRenderer()),
            ErrorRendererRegistration(CoffeeError, CoffeeErrorRenderer()),
            ErrorRendererRegistration(RegistrationError, RegistrationErrorRenderer()),
        )
    )
