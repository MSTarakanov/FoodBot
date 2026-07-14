from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
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


class PollKind(StrEnum):
    LUNCH_ATTENDANCE_V1 = "lunch_attendance_v1"
    LUNCH_PLACE_SKYLINE_V1 = "lunch_place_skyline_v1"
    LUNCH_PLACE_ROSE_V1 = "lunch_place_rose_v1"
    LUNCH_OTHER_FOOD_V1 = "lunch_other_food_v1"


class CoffeeSessionStatus(StrEnum):
    CREATING = "creating"
    ACTIVE = "active"
    COMPLETING = "completing"
    COMPLETED = "completed"
    EXPIRED = "expired"
    FAILED = "failed"


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
class KnownTelegramAccount:
    telegram_user_id: int
    username: str | None
    first_name: str | None
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
    email: str | None


@dataclass(frozen=True)
class RegistrationDetails:
    display_name: str
    splitwise: SplitwiseConnection | None


@dataclass(frozen=True, slots=True)
class InvitationPreferences:
    lunch_enabled: bool = True
    coffee_enabled: bool = True


@dataclass(frozen=True)
class PendingRegistration:
    user: RegisteredUser
    splitwise: SplitwiseConnection | None


@dataclass(frozen=True)
class ActiveSplitwiseUser:
    username: str | None
    display_name: str
    splitwise_user_id: int
    email: str | None


@dataclass(frozen=True)
class LunchAutoChat:
    chat_id: int
    title: str | None
    enabled: bool


@dataclass(frozen=True)
class LunchPinnedMessage:
    chat_id: int
    message_id: int
    lunch_date: date


@dataclass(frozen=True)
class UserVacation:
    user_id: int
    until_date: date


@dataclass(frozen=True)
class StoredPoll:
    poll_id: str
    chat_id: int
    message_id: int
    kind: PollKind
    context_date: date
    published_at: datetime


@dataclass(frozen=True)
class CoffeeSession:
    id: int
    chat_id: int
    message_id: int | None
    initiator_user_id: int
    last_proposer_user_id: int
    scheduled_at: datetime
    status: CoffeeSessionStatus
    notification_attempts: int
    next_attempt_at: datetime | None
    retry_until: datetime | None
