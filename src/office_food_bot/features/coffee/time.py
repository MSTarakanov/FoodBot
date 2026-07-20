from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from math import ceil
from zoneinfo import ZoneInfo

from office_food_bot.features.coffee.models import (
    CoffeeTimeResolution,
    CoffeeTimeResolutionKind,
)


class CoffeeTimeResolver:
    def __init__(
        self,
        timezone_name: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._timezone = ZoneInfo(timezone_name)
        self._clock = clock or (lambda: datetime.now(tz=UTC))

    def resolve(self, raw_value: str) -> CoffeeTimeResolution:
        now = self._clock()
        scheduled_at = parse_coffee_time(raw_value, now, self._timezone)
        if scheduled_at is None:
            return CoffeeTimeResolution(CoffeeTimeResolutionKind.INVALID_FORMAT)
        if not _is_allowed_time(scheduled_at, now, self._timezone):
            return CoffeeTimeResolution(CoffeeTimeResolutionKind.OUT_OF_RANGE)
        return CoffeeTimeResolution(CoffeeTimeResolutionKind.VALID, scheduled_at)


def parse_coffee_time(
    raw_value: str,
    now: datetime,
    timezone: ZoneInfo,
) -> datetime | None:
    value = raw_value.strip()
    local_now = now.astimezone(timezone)
    if value.isdigit():
        minutes = int(value)
        if minutes <= 0:
            return None
        return (local_now + timedelta(minutes=minutes)).astimezone(UTC)
    if re.fullmatch(r"\d{2}:\d{2}", value) is None:
        return None
    try:
        parsed_time = time.fromisoformat(value)
    except ValueError:
        return None
    if parsed_time.second or parsed_time.microsecond:
        return None
    return datetime.combine(local_now.date(), parsed_time, tzinfo=timezone).astimezone(UTC)


def next_coffee_countdown_update(
    scheduled_at: datetime,
    now: datetime,
) -> datetime | None:
    remaining_seconds = (scheduled_at - now).total_seconds()
    if remaining_seconds <= 60:
        return None
    if remaining_seconds >= timedelta(minutes=60).total_seconds():
        return scheduled_at - timedelta(minutes=59)
    displayed_minutes = ceil(remaining_seconds / 60)
    return scheduled_at - timedelta(minutes=displayed_minutes - 1)


def _is_allowed_time(
    scheduled_at: datetime,
    now: datetime,
    timezone: ZoneInfo,
) -> bool:
    local_scheduled = scheduled_at.astimezone(timezone)
    local_now = now.astimezone(timezone)
    return (
        local_scheduled.date() == local_now.date()
        and scheduled_at >= now + timedelta(minutes=1)
    )
