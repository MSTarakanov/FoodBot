from __future__ import annotations

import re

from office_food_bot.commanding.errors.models import CommandInputError, InputErrorCode
from office_food_bot.presence_models import EtaRequest

MAX_ETA_MINUTES = 366 * 24 * 60
_SINGLE_ETA_REQUEST_PATTERN = re.compile(r"\s*-?\d+\s*")
_ETA_REQUEST_PATTERN = re.compile(r"\s*(\d+)(?:\s*-\s*(\d+))?\s*")


class EtaRequestParser:
    def parse(self, raw_arguments: str | None) -> EtaRequest:
        raw_minutes = raw_arguments or ""
        if not raw_minutes.strip():
            raise CommandInputError(InputErrorCode.MISSING)

        match = _ETA_REQUEST_PATTERN.fullmatch(raw_minutes)
        if match is None:
            if _SINGLE_ETA_REQUEST_PATTERN.fullmatch(raw_minutes) is not None:
                raise CommandInputError(InputErrorCode.OUT_OF_RANGE)
            raise CommandInputError(InputErrorCode.INVALID_FORMAT)

        start_minutes = int(match.group(1))
        if not _is_valid_eta_minutes(start_minutes):
            raise CommandInputError(InputErrorCode.OUT_OF_RANGE)

        end_minutes_raw = match.group(2)
        if end_minutes_raw is None:
            return EtaRequest(start_minutes)

        end_minutes = int(end_minutes_raw)
        if not _is_valid_eta_minutes(end_minutes):
            raise CommandInputError(InputErrorCode.OUT_OF_RANGE)
        if start_minutes > end_minutes:
            raise CommandInputError(InputErrorCode.REVERSED_RANGE)
        return EtaRequest(start_minutes, end_minutes)


def _is_valid_eta_minutes(minutes: int) -> bool:
    return 0 <= minutes <= MAX_ETA_MINUTES
