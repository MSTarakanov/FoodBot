from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class UserStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"
    DISABLED = "disabled"


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
