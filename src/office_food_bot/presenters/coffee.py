from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from html import escape
from math import ceil
from typing import assert_never
from zoneinfo import ZoneInfo

from office_food_bot.coffee_models import (
    CoffeeParticipationKind,
    CoffeeParticipationReport,
    CoffeeStatusReport,
)
from office_food_bot.models import CoffeeSession, RegisteredUser

COFFEE_TIME_USAGE = "Создать или перенести встречу: /coffee 15 или /coffee 16:30."
COFFEE_COUNTDOWN_WINDOW = timedelta(minutes=60)


class CoffeeCardRenderer:
    def __init__(self, timezone_name: str) -> None:
        self._timezone = ZoneInfo(timezone_name)

    def render(
        self,
        session: CoffeeSession,
        proposer: RegisteredUser,
        participants: Sequence[RegisteredUser],
        now: datetime,
    ) -> str:
        local_time = session.scheduled_at.astimezone(self._timezone).strftime("%H:%M")
        lines = [
            f"☕ {escape(proposer.display_name)} предлагает кофе",
            f"Время: <b>{local_time}</b>",
        ]
        if _coffee_countdown_is_visible(session.scheduled_at, now):
            countdown = coffee_countdown_text(session.scheduled_at, now)
            lines.append(f"Через: <b>{countdown}</b>")
        return self._with_participants(lines, participants)

    def render_completed(
        self,
        session: CoffeeSession,
        proposer: RegisteredUser,
        participants: Sequence[RegisteredUser],
    ) -> str:
        local_time = session.scheduled_at.astimezone(self._timezone).strftime("%H:%M")
        lines = [
            f"☕ {escape(proposer.display_name)} предлагает кофе",
            f"Время: <b>{local_time}</b>",
            "Встреча прошла",
        ]
        return self._with_participants(lines, participants)

    def _with_participants(
        self,
        lines: list[str],
        participants: Sequence[RegisteredUser],
    ) -> str:
        lines.extend(("", f"Идут ({len(participants)}):"))
        if participants:
            lines.extend(f"• {escape(user.display_name)}" for user in participants)
        else:
            lines.append("Пока никто")
        return "\n".join(lines)


class CoffeeCommandRenderer:
    def __init__(self, timezone_name: str) -> None:
        self._timezone = ZoneInfo(timezone_name)

    def status(self, report: CoffeeStatusReport) -> str:
        invitations = "включены" if report.invitations_enabled else "выключены"
        lines = [
            f"Приглашения на кофе: {invitations}.",
            "",
            COFFEE_TIME_USAGE,
            "",
        ]
        if report.scheduled_at is None:
            lines.append("Текущей встречи нет.")
            return "\n".join(lines)
        local_time = report.scheduled_at.astimezone(self._timezone).strftime("%H:%M")
        names = ", ".join(report.participant_names)
        lines.append(f"Текущая встреча: {local_time}")
        lines.append(f"Идут: {names or 'пока никто'}")
        return "\n".join(lines)

    def participation(self, report: CoffeeParticipationReport) -> str | None:
        match report.kind:
            case CoffeeParticipationKind.JOINED:
                return "Ты идешь на кофе."
            case CoffeeParticipationKind.LEFT:
                return "Ты больше не идешь на кофе."
            case CoffeeParticipationKind.UNCHANGED:
                return None
        assert_never(report.kind)


def coffee_countdown_text(scheduled_at: datetime, now: datetime) -> str:
    remaining_seconds = (scheduled_at - now).total_seconds()
    if remaining_seconds <= 0:
        return "сейчас"
    minutes = ceil(remaining_seconds / 60)
    return f"{minutes} {_minute_word(minutes)}"


def _coffee_countdown_is_visible(scheduled_at: datetime, now: datetime) -> bool:
    remaining = scheduled_at - now
    return timedelta() < remaining < COFFEE_COUNTDOWN_WINDOW


def _minute_word(minutes: int) -> str:
    last_two_digits = minutes % 100
    if 11 <= last_two_digits <= 14:
        return "минут"
    last_digit = minutes % 10
    if last_digit == 1:
        return "минуту"
    if 2 <= last_digit <= 4:
        return "минуты"
    return "минут"
