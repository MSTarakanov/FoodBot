from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from aiogram import Bot

from office_food_bot.features.coffee.locks import CoffeeChatLocks
from office_food_bot.features.coffee.models import CoffeeSession, CoffeeSessionStatus
from office_food_bot.features.coffee.ports import CoffeeScheduler, CoffeeSessionStore
from office_food_bot.features.coffee.publisher import CoffeeCardPublisher
from office_food_bot.features.coffee.time import next_coffee_countdown_update

logger = logging.getLogger(__name__)

RETRY_DELAYS = (timedelta(minutes=1), timedelta(minutes=3), timedelta(minutes=5))
RECOVERY_GRACE = timedelta(minutes=5)


class CoffeeJobCoordinator:
    def __init__(
        self,
        sessions: CoffeeSessionStore,
        publisher: CoffeeCardPublisher,
        scheduler: CoffeeScheduler,
        locks: CoffeeChatLocks,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._sessions = sessions
        self._publisher = publisher
        self._scheduler = scheduler
        self._locks = locks
        self._clock = clock or (lambda: datetime.now(tz=UTC))

    def schedule_session(self, bot: Bot, session: CoffeeSession) -> None:
        self._schedule_completion(bot, session)
        self._schedule_countdown(bot, session)

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
                await self._publisher.replace_pin(bot, None, session)
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
                run_at = max(session.next_attempt_at or now, now)
            self._schedule_completion_at(bot, session.id, run_at)

    async def complete(self, bot: Bot, session_id: int) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        async with self._locks.for_chat(session.chat_id):
            session = self._sessions.get(session_id)
            if session is None or session.status not in {
                CoffeeSessionStatus.ACTIVE,
                CoffeeSessionStatus.COMPLETING,
            }:
                return
            now = self._clock()
            self._scheduler.remove(_coffee_countdown_job_id(session.id))
            await self._publisher.unpin(bot, session)
            if session.status == CoffeeSessionStatus.ACTIVE:
                session = self._sessions.mark_completing(
                    session.id,
                    session.scheduled_at + RETRY_DELAYS[-1],
                )
            participants = self._sessions.list_participants(session.id)
            await self._publisher.mark_card_completed(bot, session, participants)
            if not participants:
                self._sessions.mark_terminal(
                    session.id,
                    CoffeeSessionStatus.COMPLETED,
                    now,
                )
                return
            if await self._publisher.send_ready_notification(
                bot,
                session,
                participants,
            ):
                self._sessions.mark_terminal(
                    session.id,
                    CoffeeSessionStatus.COMPLETED,
                    now,
                )
                return
            self._schedule_retry(bot, session, now)

    async def refresh_countdown(self, bot: Bot, session_id: int) -> None:
        session = self._sessions.get(session_id)
        if session is None or session.status != CoffeeSessionStatus.ACTIVE:
            self._scheduler.remove(_coffee_countdown_job_id(session_id))
            return
        async with self._locks.for_chat(session.chat_id):
            current = self._sessions.get(session_id)
            if current is None or current.status != CoffeeSessionStatus.ACTIVE:
                self._scheduler.remove(_coffee_countdown_job_id(session_id))
                return
            self._schedule_countdown(bot, current)
            updated = await self._publish_card(bot, current)
            await self._publisher.replace_pin(bot, current, updated)

    def _schedule_recovery(self, bot: Bot, session_id: int, run_at: datetime) -> None:
        async def run() -> None:
            session = self._sessions.get(session_id)
            if session is None:
                return
            async with self._locks.for_chat(session.chat_id):
                current = self._sessions.get(session_id)
                if current is None or current.status != CoffeeSessionStatus.CREATING:
                    return
                try:
                    current = await self._publish_card(bot, current)
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
                    raise RuntimeError("Recovered coffee card has no message id")
                current = self._sessions.activate(current.id, current.message_id)
                await self._publisher.replace_pin(bot, None, current)
                self.schedule_session(bot, current)

        self._scheduler.add_date(f"coffee_recovery:{session_id}", run, run_at)

    def _schedule_retry(
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
        next_attempt = max(
            session.scheduled_at + RETRY_DELAYS[attempts - 1],
            now,
        )
        self._sessions.mark_retry(session.id, attempts, next_attempt)
        self._schedule_completion_at(bot, session.id, next_attempt)

    async def _publish_card(
        self,
        bot: Bot,
        session: CoffeeSession,
    ) -> CoffeeSession:
        participants = self._sessions.list_participants(session.id)
        message_id = await self._publisher.publish_card(bot, session, participants)
        if session.message_id != message_id:
            return self._sessions.update_message(session.id, message_id)
        return session

    def _schedule_completion(self, bot: Bot, session: CoffeeSession) -> None:
        self._schedule_completion_at(bot, session.id, session.scheduled_at)

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

    def _schedule_completion_at(
        self,
        bot: Bot,
        session_id: int,
        run_at: datetime,
    ) -> None:
        async def run() -> None:
            await self.complete(bot, session_id)

        self._scheduler.add_date(_coffee_job_id(session_id), run, run_at)


def _coffee_job_id(session_id: int) -> str:
    return f"coffee_session:{session_id}"


def _coffee_countdown_job_id(session_id: int) -> str:
    return f"coffee_countdown:{session_id}"
