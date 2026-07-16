from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class VacationReportKind(StrEnum):
    STATUS_ACTIVE = "status_active"
    STATUS_INACTIVE = "status_inactive"
    CLEARED = "cleared"
    SET = "set"


@dataclass(frozen=True, slots=True)
class VacationReport:
    kind: VacationReportKind
    display_name: str
    until_date: date | None = None
