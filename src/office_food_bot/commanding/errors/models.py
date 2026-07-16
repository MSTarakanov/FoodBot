from __future__ import annotations

from enum import StrEnum


class UserFacingError(Exception):
    pass


class CommonUserError(UserFacingError):
    pass


class CommonErrorCode(StrEnum):
    MISSING_TELEGRAM_IDENTITY = "missing_telegram_identity"
    PRIVATE_CHAT_REQUIRED = "private_chat_required"
    GROUP_CHAT_REQUIRED = "group_chat_required"
    ADMIN_REQUIRED = "admin_required"
    REGISTRATION_REQUIRED = "registration_required"
    REGISTRATION_PENDING = "registration_pending"
    REGISTRATION_INACTIVE = "registration_inactive"
    INTERNAL = "internal"


class CommonError(CommonUserError):
    def __init__(self, code: CommonErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


class InputErrorCode(StrEnum):
    MISSING = "missing"
    INVALID_FORMAT = "invalid_format"
    INVALID_CHOICE = "invalid_choice"
    OUT_OF_RANGE = "out_of_range"
    REVERSED_RANGE = "reversed_range"


class CommandInputError(CommonUserError):
    def __init__(self, code: InputErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


class ExternalDependency(StrEnum):
    SPLITWISE = "splitwise"


class InfrastructureUnavailableError(CommonUserError):
    def __init__(self, dependency: ExternalDependency) -> None:
        super().__init__(dependency.value)
        self.dependency = dependency


class BalanceErrorCode(StrEnum):
    NO_SPLITWISE_USERS = "no_splitwise_users"


class BalanceError(UserFacingError):
    def __init__(self, code: BalanceErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


class CoffeeErrorCode(StrEnum):
    INVALID_CALLBACK = "invalid_callback"
    SESSION_ENDED = "session_ended"


class CoffeeError(UserFacingError):
    def __init__(self, code: CoffeeErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


class RegistrationErrorCode(StrEnum):
    REQUEST_ALREADY_PENDING = "request_already_pending"
    REQUEST_ALREADY_ACTIVE = "request_already_active"
    REQUEST_UNAVAILABLE = "request_unavailable"


class RegistrationError(UserFacingError):
    def __init__(self, code: RegistrationErrorCode) -> None:
        super().__init__(code.value)
        self.code = code
