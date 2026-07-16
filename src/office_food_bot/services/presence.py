from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from office_food_bot.presence_models import EtaRequest, PresenceKind, PresenceReport
from office_food_bot.services.user_access import ActiveUserResolver


class PresenceService:
    def __init__(
        self,
        active_users: ActiveUserResolver,
        timezone_name: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._active_users = active_users
        self._timezone = ZoneInfo(timezone_name)
        self._clock = clock or (lambda: datetime.now(tz=UTC))

    def report(
        self,
        telegram_user_id: int,
        request: EtaRequest,
        kind: PresenceKind,
    ) -> PresenceReport:
        user = self._active_users.require(telegram_user_id)
        now = self._local_now()
        return PresenceReport(
            kind=kind,
            user=user,
            start=now + timedelta(minutes=request.start_minutes),
            end=(
                None
                if request.end_minutes is None
                else now + timedelta(minutes=request.end_minutes)
            ),
            reference_date=now.date(),
        )

    def _local_now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        return now.astimezone(self._timezone)
