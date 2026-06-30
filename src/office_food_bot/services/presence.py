from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from office_food_bot.models import UserStatus
from office_food_bot.repositories import UserRepository


class PresenceService:
    def __init__(
        self,
        users: UserRepository,
        timezone_name: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._users = users
        self._timezone = ZoneInfo(timezone_name)
        self._clock = clock or (lambda: datetime.now(tz=UTC))

    def meta(self, telegram_user_id: int, raw_minutes: str) -> str:
        user = self._users.get_by_telegram_id(telegram_user_id)
        if user is None:
            return "Сначала зарегистрируйся: /register Имя"
        if user.status == UserStatus.PENDING:
            return "Регистрация еще ждет аппрува."
        if user.status != UserStatus.ACTIVE:
            return "Регистрация сейчас неактивна."

        minutes = _parse_minutes(raw_minutes)
        if minutes is None:
            return "Минуты должны быть положительным числом: /meta 25"

        now = self._clock()
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        eta = now.astimezone(self._timezone) + timedelta(minutes=minutes)
        return f"{user.display_name} будет в {eta:%H:%M}"


def _parse_minutes(raw_minutes: str) -> int | None:
    try:
        minutes = int(raw_minutes.strip())
    except ValueError:
        return None
    if minutes <= 0:
        return None
    if minutes > 24 * 60:
        return None
    return minutes
