from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from office_food_bot.models import RegisteredUser


class PresenceKind(StrEnum):
    META = "meta"
    DELIVERY_ETA = "eta"


@dataclass(frozen=True, slots=True)
class EtaRequest:
    start_minutes: int
    end_minutes: int | None = None


@dataclass(frozen=True, slots=True)
class PresenceReport:
    kind: PresenceKind
    user: RegisteredUser
    start: datetime
    end: datetime | None
    reference_date: date
