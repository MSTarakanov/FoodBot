from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class CoffeeStatusReport:
    invitations_enabled: bool
    scheduled_at: datetime | None
    participant_names: tuple[str, ...]


class CoffeeParticipationKind(StrEnum):
    JOINED = "joined"
    LEFT = "left"
    UNCHANGED = "unchanged"


@dataclass(frozen=True, slots=True)
class CoffeeParticipationReport:
    kind: CoffeeParticipationKind


class CoffeeTimeResolutionKind(StrEnum):
    VALID = "valid"
    INVALID_FORMAT = "invalid_format"
    OUT_OF_RANGE = "out_of_range"


@dataclass(frozen=True, slots=True)
class CoffeeTimeResolution:
    kind: CoffeeTimeResolutionKind
    scheduled_at: datetime | None = None


class CoffeeSessionStatus(StrEnum):
    CREATING = "creating"
    ACTIVE = "active"
    COMPLETING = "completing"
    COMPLETED = "completed"
    EXPIRED = "expired"
    FAILED = "failed"


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
