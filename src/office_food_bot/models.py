from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class UserStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"
    DISABLED = "disabled"
    ABANDONED = "abandoned"


class UserRole(StrEnum):
    MEMBER = "member"
    ADMIN = "admin"


class RegistrationKind(StrEnum):
    CREATED = "created"
    UPDATED_PENDING = "updated_pending"
    ALREADY_ACTIVE = "already_active"
    ALREADY_PENDING = "already_pending"
    BLOCKED = "blocked"


class ApprovalKind(StrEnum):
    APPROVED = "approved"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class TelegramProfile:
    telegram_user_id: int
    username: str | None
    first_name: str
    last_name: str | None


@dataclass(frozen=True)
class RegisteredUser:
    id: int
    telegram_user_id: int
    display_name: str
    status: UserStatus
    role: UserRole
    username: str | None
    first_name: str | None
    last_name: str | None


@dataclass(frozen=True)
class SplitwiseBalance:
    currency_code: str
    amount: Decimal


@dataclass(frozen=True)
class SplitwiseMember:
    splitwise_user_id: int
    first_name: str
    last_name: str | None
    email: str
    balance: tuple[SplitwiseBalance, ...] = ()


@dataclass(frozen=True)
class SplitwiseConnection:
    splitwise_user_id: int
    email: str


@dataclass(frozen=True)
class RegistrationDetails:
    display_name: str
    splitwise: SplitwiseConnection | None


@dataclass(frozen=True)
class PendingRegistration:
    user: RegisteredUser
    splitwise: SplitwiseConnection | None


@dataclass(frozen=True)
class ActiveSplitwiseUser:
    display_name: str
    splitwise_user_id: int
    email: str


@dataclass(frozen=True)
class LunchAutoChat:
    chat_id: int
    title: str | None
    enabled: bool


@dataclass(frozen=True)
class UserVacation:
    user_id: int
    until_date: date
