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
