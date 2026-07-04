from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from office_food_bot.models import RegisteredUser, UserStatus
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
        block_reason = _registration_block_reason(user)
        if block_reason is not None:
            return block_reason
        assert user is not None

        minutes = _parse_minutes(raw_minutes)
        if minutes is None:
            return "Минуты должны быть положительным числом: /meta 25"

        eta = self._eta(minutes)
        return f"{user.display_name} будет в {eta:%H:%M}"

    def delivery_eta(self, telegram_user_id: int, raw_minutes: str) -> str:
        user = self._users.get_by_telegram_id(telegram_user_id)
        block_reason = _registration_block_reason(user)
        if block_reason is not None:
            return block_reason

        minutes = _parse_minutes(raw_minutes)
        if minutes is None:
            return "Минуты должны быть положительным числом: /eta 20"

        eta = self._eta(minutes)
        return f"Ожидаемое время прибытия доставки {eta:%H:%M}"

    def _eta(self, minutes: int) -> datetime:
        now = self._clock()
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        return now.astimezone(self._timezone) + timedelta(minutes=minutes)


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


def _registration_block_reason(user: RegisteredUser | None) -> str | None:
    if user is None:
        return "Сначала зарегистрируйся: /register"
    if user.status == UserStatus.PENDING:
        return "Регистрация еще ждет аппрува."
    if user.status != UserStatus.ACTIVE:
        return "Регистрация сейчас неактивна."
    return None
