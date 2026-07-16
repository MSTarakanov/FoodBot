from __future__ import annotations

import re
from dataclasses import dataclass

from office_food_bot.commanding.errors.models import InputErrorCode
from office_food_bot.features.presence.models import EtaRequest
from office_food_bot.result import Result, failure, success

MAX_ETA_MINUTES = 366 * 24 * 60
_SINGLE_ETA_REQUEST_PATTERN = re.compile(r"\s*-?\d+\s*")
_ETA_REQUEST_PATTERN = re.compile(r"\s*(\d+)(?:\s*-\s*(\d+))?\s*")


@dataclass(frozen=True, slots=True)
class EtaInput:
    raw_minutes: str


class EtaRequestParser:
    def parse(
        self,
        raw_arguments: str | None,
    ) -> EtaInput:
        return EtaInput(raw_arguments or "")


class EtaRequestResolver:
    def resolve(
        self,
        value: EtaInput,
    ) -> Result[EtaRequest, InputErrorCode]:
        raw_minutes = value.raw_minutes
        if not raw_minutes.strip():
            return failure(InputErrorCode.MISSING)

        match = _ETA_REQUEST_PATTERN.fullmatch(raw_minutes)
        if match is None:
            if _SINGLE_ETA_REQUEST_PATTERN.fullmatch(raw_minutes) is not None:
                return failure(InputErrorCode.OUT_OF_RANGE)
            return failure(InputErrorCode.INVALID_FORMAT)

        start_minutes = int(match.group(1))
        if not _is_valid_eta_minutes(start_minutes):
            return failure(InputErrorCode.OUT_OF_RANGE)

        end_minutes_raw = match.group(2)
        if end_minutes_raw is None:
            return success(EtaRequest(start_minutes))

        end_minutes = int(end_minutes_raw)
        if not _is_valid_eta_minutes(end_minutes):
            return failure(InputErrorCode.OUT_OF_RANGE)
        if start_minutes > end_minutes:
            return failure(InputErrorCode.REVERSED_RANGE)
        return success(EtaRequest(start_minutes, end_minutes))


def _is_valid_eta_minutes(minutes: int) -> bool:
    return 0 <= minutes <= MAX_ETA_MINUTES
