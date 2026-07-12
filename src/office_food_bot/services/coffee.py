from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from html import escape
from math import ceil
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.enums import ParseMode

from office_food_bot.coffee_callbacks import CoffeeCallbackData, CoffeeParticipantAction
from office_food_bot.coffee_repositories import CoffeeSessionRepository
from office_food_bot.messaging import BotMessenger, InlineChoice
from office_food_bot.models import CoffeeSession, CoffeeSessionStatus, RegisteredUser, UserStatus
from office_food_bot.repositories import UserRepository
from office_food_bot.services.invitations import (
    InvitationPreferenceService,
    registration_required_text,
)
from office_food_bot.services.job_scheduler import JobScheduler
from office_food_bot.services.lunch_attendance import LunchAttendanceService
from office_food_bot.services.user_references import format_user_reference

logger = logging.getLogger(__name__)

COFFEE_TIME_USAGE = "Создать или перенести встречу: /coffee 15 или /coffee 16:30."
COFFEE_TIME_ERROR = (
    "Не понял время. Напиши минуты или время сегодня: /coffee 15 или /coffee 16:30."
)
COFFEE_TIME_RANGE_ERROR = "Время кофе должно быть минимум через минуту и до конца сегодня."
RETRY_DELAYS = (timedelta(minutes=1), timedelta(minutes=3), timedelta(minutes=5))
RECOVERY_GRACE = timedelta(minutes=5)
COFFEE_COUNTDOWN_WINDOW = timedelta(minutes=60)


@dataclass(frozen=True, slots=True)
class CoffeeUserAccess:
    user: RegisteredUser | None
    denial_text: str | None


@dataclass(frozen=True, slots=True)
class CoffeeParticipationResult:
    text: str | None
    show_alert: bool


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


class CoffeeService:
    def __init__(
        self,
        users: UserRepository,
        preferences: InvitationPreferenceService,
        sessions: CoffeeSessionRepository,
        attendance: LunchAttendanceService,
        messenger: BotMessenger,
        scheduler: JobScheduler,
        timezone_name: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._users = users
        self._preferences = preferences
        self._sessions = sessions
        self._attendance = attendance
        self._messenger = messenger
        self._scheduler = scheduler
        self._timezone = ZoneInfo(timezone_name)
        self._renderer = CoffeeCardRenderer(timezone_name)
        self._clock = clock or (lambda: datetime.now(tz=UTC))
        self._chat_locks: dict[int, asyncio.Lock] = {}

    def status_text(self, telegram_user_id: int, chat_id: int) -> str:
        access = self._active_user(telegram_user_id)
        if access.user is None:
            return access.denial_text or "Регистрация сейчас неактивна."
        user = access.user
        invitations = (
            "включены"
            if self._preferences.for_user(user.id).coffee_enabled
            else "выключены"
        )
        session = self._sessions.get_open_for_chat(chat_id)
        lines = [
            f"Приглашения на кофе: {invitations}.",
            "",
            COFFEE_TIME_USAGE,
            "",
        ]
        if session is None:
            lines.append("Текущей встречи нет.")
            return "\n".join(lines)
        participants = self._sessions.list_participants(session.id)
        local_time = session.scheduled_at.astimezone(self._timezone).strftime("%H:%M")
        names = ", ".join(participant.display_name for participant in participants)
        lines.append(f"Текущая встреча: {local_time}")
        lines.append(f"Идут: {names or 'пока никто'}")
        return "\n".join(lines)

    def set_invitations(self, telegram_user_id: int, enabled: bool) -> str:
        access = self._active_user(telegram_user_id)
        if access.user is None:
            return access.denial_text or "Регистрация сейчас неактивна."
        return self._preferences.set_coffee(telegram_user_id, enabled)

    async def create_or_reschedule(
        self,
        bot: Bot,
        chat_id: int,
        telegram_user_id: int,
        raw_time: str,
    ) -> str | None:
        access = self._active_user(telegram_user_id)
        if access.user is None:
            return access.denial_text or "Регистрация сейчас неактивна."
        user = access.user
        scheduled_at = parse_coffee_time(raw_time, self._clock(), self._timezone)
        if scheduled_at is None:
            return COFFEE_TIME_ERROR
        if not _is_allowed_time(scheduled_at, self._clock(), self._timezone):
            return COFFEE_TIME_RANGE_ERROR

        async with self._lock(chat_id):
            session = self._sessions.get_open_for_chat(chat_id)
            is_new = session is None
            previous_session = session
            previous_participant_ids: set[int] = set()
            if session is None:
                session = self._sessions.create(chat_id, user.id, scheduled_at)
            else:
                previous_participant_ids = {
                    participant.id
                    for participant in self._sessions.list_participants(session.id)
                }
                session = self._sessions.reschedule(session.id, user.id, scheduled_at)
            try:
                session = await self._update_card(bot, session)
            except Exception:
                if is_new:
                    self._sessions.mark_terminal(
                        session.id,
                        CoffeeSessionStatus.FAILED,
                        self._clock(),
                    )
                elif previous_session is not None:
                    self._sessions.reschedule(
                        session.id,
                        previous_session.last_proposer_user_id,
                        previous_session.scheduled_at,
                    )
                    if user.id not in previous_participant_ids:
                        self._sessions.leave(session.id, user.id)
                raise
            if session.status == CoffeeSessionStatus.CREATING:
                if session.message_id is None:
                    msg = "Created coffee card has no message id"
                    raise RuntimeError(msg)
                session = self._sessions.activate(session.id, session.message_id)
            self._schedule_completion(bot, session)
            self._schedule_countdown(bot, session)
            await self._replace_pin(bot, previous_session, session)
            if is_new:
                await self._send_shout(bot, session)
            elif (
                previous_session is not None
                and previous_session.scheduled_at != session.scheduled_at
            ):
                await self._send_reschedule_notification(bot, user, session)
        return None

    async def update_participation(
        self,
        bot: Bot,
        telegram_user_id: int,
        callback: CoffeeCallbackData,
    ) -> CoffeeParticipationResult:
        access = self._active_user(telegram_user_id)
        if access.user is None:
            return CoffeeParticipationResult(
                access.denial_text or "Регистрация сейчас неактивна.",
                True,
            )
        user = access.user
        session = self._sessions.get(callback.session_id)
        if session is None or session.status != CoffeeSessionStatus.ACTIVE:
            return CoffeeParticipationResult("Эта встреча уже завершена.", True)
        async with self._lock(session.chat_id):
            current = self._sessions.get(callback.session_id)
            if current is None or current.status != CoffeeSessionStatus.ACTIVE:
                return CoffeeParticipationResult("Эта встреча уже завершена.", True)
            participant_ids = {
                participant.id
                for participant in self._sessions.list_participants(current.id)
            }
            was_participant = user.id in participant_ids
            if callback.action == CoffeeParticipantAction.JOIN:
                if was_participant:
                    return CoffeeParticipationResult(None, False)
                self._sessions.join(current.id, user.id)
                reply = "Ты идешь на кофе."
            else:
                if not was_participant:
                    return CoffeeParticipationResult(None, False)
                self._sessions.leave(current.id, user.id)
                reply = "Ты больше не идешь на кофе."
            try:
                updated = await self._update_card(bot, current)
                await self._replace_pin(bot, current, updated)
            except Exception:
                if was_participant:
                    self._sessions.join(current.id, user.id)
                else:
                    self._sessions.leave(current.id, user.id)
                raise
            return CoffeeParticipationResult(reply, False)

    async def restore_jobs(self, bot: Bot) -> None:
        now = self._clock()
        for session in self._sessions.list_recoverable():
            if session.status == CoffeeSessionStatus.CREATING:
                if now - session.scheduled_at > RECOVERY_GRACE:
                    self._sessions.mark_terminal(
                        session.id,
                        CoffeeSessionStatus.EXPIRED,
                        now,
                    )
                    continue
                self._schedule_recovery(bot, session.id, now)
                continue
            if session.status == CoffeeSessionStatus.ACTIVE:
                overdue = now - session.scheduled_at
                if overdue > RECOVERY_GRACE:
                    self._sessions.mark_terminal(
                        session.id,
                        CoffeeSessionStatus.EXPIRED,
                        now,
                    )
                    continue
                if session.message_id is not None:
                    await self._messenger.try_pin_chat_message(
                        bot,
                        session.chat_id,
                        session.message_id,
                    )
                self._schedule_countdown(bot, session)
                run_at = max(session.scheduled_at, now)
            else:
                if session.retry_until is not None and session.retry_until < now:
                    self._sessions.mark_terminal(
                        session.id,
                        CoffeeSessionStatus.FAILED,
                        now,
                    )
                    continue
                run_at = session.next_attempt_at or now
                run_at = max(run_at, now)
            self._schedule_job(bot, session.id, run_at)

    def _schedule_recovery(self, bot: Bot, session_id: int, run_at: datetime) -> None:
        async def run() -> None:
            session = self._sessions.get(session_id)
            if session is None:
                return
            async with self._lock(session.chat_id):
                current = self._sessions.get(session_id)
                if current is None or current.status != CoffeeSessionStatus.CREATING:
                    return
                try:
                    current = await self._update_card(bot, current)
                except Exception:
                    logger.exception(
                        "Coffee creating-session recovery failed: session_id=%s",
                        session_id,
                    )
                    self._sessions.mark_terminal(
                        session_id,
                        CoffeeSessionStatus.FAILED,
                        self._clock(),
                    )
                    return
                if current.message_id is None:
                    msg = "Recovered coffee card has no message id"
                    raise RuntimeError(msg)
                current = self._sessions.activate(current.id, current.message_id)
                await self._replace_pin(bot, None, current)
                self._schedule_completion(bot, current)
                self._schedule_countdown(bot, current)

        self._scheduler.add_date(f"coffee_recovery:{session_id}", run, run_at)

    async def complete(self, bot: Bot, session_id: int) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        async with self._lock(session.chat_id):
            session = self._sessions.get(session_id)
            if session is None or session.status not in {
                CoffeeSessionStatus.ACTIVE,
                CoffeeSessionStatus.COMPLETING,
            }:
                return
            now = self._clock()
            self._scheduler.remove(_coffee_countdown_job_id(session.id))
            if session.message_id is not None:
                await self._messenger.try_unpin_chat_message(
                    bot,
                    session.chat_id,
                    session.message_id,
                )
            if session.status == CoffeeSessionStatus.ACTIVE:
                session = self._sessions.mark_completing(
                    session.id,
                    session.scheduled_at + RETRY_DELAYS[-1],
                )
            participants = self._sessions.list_participants(session.id)
            await self._mark_card_completed(bot, session, participants)
            if not participants:
                self._sessions.mark_terminal(
                    session.id,
                    CoffeeSessionStatus.COMPLETED,
                    now,
                )
                return
            references = " ".join(format_user_reference(user) for user in participants)
            sent = await self._messenger.try_send(
                bot,
                session.chat_id,
                f"☕ Пора идти за кофе!\n{references}",
            )
            if sent:
                self._sessions.mark_terminal(
                    session.id,
                    CoffeeSessionStatus.COMPLETED,
                    now,
                )
                return
            await self._schedule_retry(bot, session, now)

    async def _schedule_retry(
        self,
        bot: Bot,
        session: CoffeeSession,
        now: datetime,
    ) -> None:
        attempts = session.notification_attempts + 1
        if attempts > len(RETRY_DELAYS):
            self._sessions.mark_terminal(
                session.id,
                CoffeeSessionStatus.FAILED,
                now,
            )
            logger.error("Coffee completion failed after retries: session_id=%s", session.id)
            return
        next_attempt = session.scheduled_at + RETRY_DELAYS[attempts - 1]
        if next_attempt < now:
            next_attempt = now
        self._sessions.mark_retry(session.id, attempts, next_attempt)
        self._schedule_job(bot, session.id, next_attempt)

    async def _update_card(self, bot: Bot, session: CoffeeSession) -> CoffeeSession:
        proposer = self._users.get_by_id(session.last_proposer_user_id)
        if proposer is None:
            msg = "Coffee proposer was not found"
            raise RuntimeError(msg)
        participants = self._sessions.list_participants(session.id)
        message = await self._messenger.edit_or_send(
            bot,
            session.chat_id,
            session.message_id,
            self._renderer.render(
                session,
                proposer,
                participants,
                self._clock(),
            ),
            reply_markup=self._messenger.inline_keyboard(
                (
                    InlineChoice(
                        "Пойду",
                        CoffeeCallbackData(
                            action=CoffeeParticipantAction.JOIN,
                            session_id=session.id,
                        ).pack(),
                    ),
                    InlineChoice(
                        "Не пойду",
                        CoffeeCallbackData(
                            action=CoffeeParticipantAction.LEAVE,
                            session_id=session.id,
                        ).pack(),
                    ),
                )
            ),
            parse_mode=ParseMode.HTML,
        )
        if session.message_id != message.message_id:
            return self._sessions.update_message(session.id, message.message_id)
        return session

    async def _mark_card_completed(
        self,
        bot: Bot,
        session: CoffeeSession,
        participants: Sequence[RegisteredUser],
    ) -> None:
        if session.message_id is None:
            return
        proposer = self._users.get_by_id(session.last_proposer_user_id)
        if proposer is None:
            return
        await self._messenger.try_edit_message(
            bot,
            session.chat_id,
            session.message_id,
            self._renderer.render_completed(session, proposer, participants),
            parse_mode=ParseMode.HTML,
        )

    async def _send_shout(self, bot: Bot, session: CoffeeSession) -> None:
        participants = self._sessions.list_participants(session.id)
        participant_ids = {participant.id for participant in participants}
        today = self._clock().astimezone(self._timezone).date()
        invitees = tuple(
            user
            for user in self._attendance.list_office_users(session.chat_id, today)
            if user.id not in participant_ids
            and self._preferences.for_user(user.id).coffee_enabled
        )
        if not invitees or session.message_id is None:
            return
        references = " ".join(format_user_reference(user) for user in invitees)
        await self._messenger.try_send(
            bot,
            session.chat_id,
            f"{references}, присоединяйтесь на кофе.",
            reply_to_message_id=session.message_id,
        )

    async def _send_reschedule_notification(
        self,
        bot: Bot,
        proposer: RegisteredUser,
        session: CoffeeSession,
    ) -> None:
        if session.message_id is None:
            return
        local_time = session.scheduled_at.astimezone(self._timezone).strftime("%H:%M")
        await self._messenger.try_send(
            bot,
            session.chat_id,
            f"{proposer.display_name} предлагает новое время кофе: {local_time}.",
            reply_to_message_id=session.message_id,
        )

    async def _replace_pin(
        self,
        bot: Bot,
        previous_session: CoffeeSession | None,
        current_session: CoffeeSession,
    ) -> None:
        if current_session.message_id is None:
            return
        previous_message_id = None
        if previous_session is not None:
            previous_message_id = previous_session.message_id
        if previous_message_id == current_session.message_id:
            return
        if (
            previous_message_id is not None
            and previous_message_id != current_session.message_id
        ):
            await self._messenger.try_unpin_chat_message(
                bot,
                current_session.chat_id,
                previous_message_id,
            )
        await self._messenger.try_pin_chat_message(
            bot,
            current_session.chat_id,
            current_session.message_id,
        )

    def _schedule_completion(self, bot: Bot, session: CoffeeSession) -> None:
        self._schedule_job(bot, session.id, session.scheduled_at)

    def _schedule_countdown(self, bot: Bot, session: CoffeeSession) -> None:
        job_id = _coffee_countdown_job_id(session.id)
        next_update = next_coffee_countdown_update(
            session.scheduled_at,
            self._clock(),
        )
        if next_update is None:
            self._scheduler.remove(job_id)
            return

        async def run() -> None:
            await self.refresh_countdown(bot, session.id)

        self._scheduler.add_date(job_id, run, next_update)

    async def refresh_countdown(self, bot: Bot, session_id: int) -> None:
        session = self._sessions.get(session_id)
        if session is None or session.status != CoffeeSessionStatus.ACTIVE:
            self._scheduler.remove(_coffee_countdown_job_id(session_id))
            return
        async with self._lock(session.chat_id):
            current = self._sessions.get(session_id)
            if current is None or current.status != CoffeeSessionStatus.ACTIVE:
                self._scheduler.remove(_coffee_countdown_job_id(session_id))
                return
            self._schedule_countdown(bot, current)
            updated = await self._update_card(bot, current)
            await self._replace_pin(bot, current, updated)

    def _schedule_job(self, bot: Bot, session_id: int, run_at: datetime) -> None:
        async def run() -> None:
            await self.complete(bot, session_id)

        self._scheduler.add_date(_coffee_job_id(session_id), run, run_at)

    def _active_user(self, telegram_user_id: int) -> CoffeeUserAccess:
        user = self._users.get_by_telegram_id(telegram_user_id)
        if user is None:
            return CoffeeUserAccess(None, registration_required_text())
        if user.status == UserStatus.PENDING:
            return CoffeeUserAccess(None, "Регистрация еще ждет аппрува.")
        if user.status != UserStatus.ACTIVE:
            return CoffeeUserAccess(None, "Регистрация сейчас неактивна.")
        return CoffeeUserAccess(user, None)

    def _lock(self, chat_id: int) -> asyncio.Lock:
        return self._chat_locks.setdefault(chat_id, asyncio.Lock())


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


def coffee_countdown_text(scheduled_at: datetime, now: datetime) -> str:
    remaining_seconds = (scheduled_at - now).total_seconds()
    if remaining_seconds <= 0:
        return "сейчас"
    minutes = ceil(remaining_seconds / 60)
    return f"{minutes} {_minute_word(minutes)}"


def next_coffee_countdown_update(
    scheduled_at: datetime,
    now: datetime,
) -> datetime | None:
    remaining_seconds = (scheduled_at - now).total_seconds()
    if remaining_seconds <= 60:
        return None
    if remaining_seconds >= COFFEE_COUNTDOWN_WINDOW.total_seconds():
        return scheduled_at - timedelta(minutes=59)
    displayed_minutes = ceil(remaining_seconds / 60)
    return scheduled_at - timedelta(minutes=displayed_minutes - 1)


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


def _coffee_job_id(session_id: int) -> str:
    return f"coffee_session:{session_id}"


def _coffee_countdown_job_id(session_id: int) -> str:
    return f"coffee_countdown:{session_id}"
