from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from office_food_bot.application.users.models import RegisteredUser


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
class SplitwiseConnection:
    splitwise_user_id: int
    email: str | None


@dataclass(frozen=True)
class RegistrationDetails:
    display_name: str
    splitwise: SplitwiseConnection | None


@dataclass(frozen=True)
class PendingRegistration:
    user: RegisteredUser
    splitwise: SplitwiseConnection | None
