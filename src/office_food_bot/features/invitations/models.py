from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class InvitationKind(StrEnum):
    LUNCH = "lunch"
    COFFEE = "coffee"


@dataclass(frozen=True, slots=True)
class InvitationSettingReport:
    kind: InvitationKind
    enabled: bool
    updated: bool
