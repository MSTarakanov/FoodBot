from __future__ import annotations

from dataclasses import dataclass
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
