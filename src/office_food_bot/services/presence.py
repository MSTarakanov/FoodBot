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
        return self._reply_with_eta(
            telegram_user_id,
            raw_minutes,
            invalid_minutes_reply="Минуты должны быть положительным числом: /meta 25",
            format_reply=_format_meta_reply,
        )

    def delivery_eta(self, telegram_user_id: int, raw_minutes: str) -> str:
        return self._reply_with_eta(
            telegram_user_id,
            raw_minutes,
            invalid_minutes_reply="Минуты должны быть положительным числом: /eta 20",
            format_reply=_format_delivery_eta_reply,
        )

    def _reply_with_eta(
        self,
        telegram_user_id: int,
        raw_minutes: str,
        *,
        invalid_minutes_reply: str,
        format_reply: Callable[[RegisteredUser, datetime], str],
    ) -> str:
        def reply_for_active_user(user: RegisteredUser) -> str:
            minutes = _parse_minutes(raw_minutes)
            if minutes is None:
                return invalid_minutes_reply

            eta = self._eta(minutes)
            return format_reply(user, eta)

        return self._reply_for_active_user(telegram_user_id, reply_for_active_user)

    def _reply_for_active_user(
        self,
        telegram_user_id: int,
        format_reply: Callable[[RegisteredUser], str],
    ) -> str:
        user = self._users.get_by_telegram_id(telegram_user_id)
        if user is None:
            return "Сначала зарегистрируйся: /register"
        if user.status == UserStatus.PENDING:
            return "Регистрация еще ждет аппрува."
        if user.status != UserStatus.ACTIVE:
            return "Регистрация сейчас неактивна."
        return format_reply(user)

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


def _format_meta_reply(user: RegisteredUser, eta: datetime) -> str:
    return f"{user.display_name} будет в {eta:%H:%M}"


def _format_delivery_eta_reply(_user: RegisteredUser, eta: datetime) -> str:
    return f"Ожидаемое время прибытия доставки {eta:%H:%M}"
