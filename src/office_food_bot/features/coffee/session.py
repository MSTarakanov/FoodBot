from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import assert_never

from aiogram import Bot

from office_food_bot.application.users.models import RegisteredUser
from office_food_bot.features.coffee.callbacks import (
    CoffeeCallbackData,
    CoffeeParticipantAction,
)
from office_food_bot.features.coffee.errors import CoffeeErrorCode
from office_food_bot.features.coffee.jobs import CoffeeJobCoordinator
from office_food_bot.features.coffee.locks import CoffeeChatLocks
from office_food_bot.features.coffee.models import (
    CoffeeParticipationKind,
    CoffeeParticipationReport,
    CoffeeSession,
    CoffeeSessionStatus,
    CoffeeStatusReport,
)
from office_food_bot.features.coffee.ports import (
    CoffeeInvitationPreferences,
    CoffeeSessionStore,
)
from office_food_bot.features.coffee.publisher import CoffeeCardPublisher
from office_food_bot.result import Result, failure, success


class CoffeeSessionService:
    def __init__(
        self,
        preferences: CoffeeInvitationPreferences,
        sessions: CoffeeSessionStore,
        publisher: CoffeeCardPublisher,
        jobs: CoffeeJobCoordinator,
        locks: CoffeeChatLocks,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._preferences = preferences
        self._sessions = sessions
        self._publisher = publisher
        self._jobs = jobs
        self._locks = locks
        self._clock = clock or (lambda: datetime.now(tz=UTC))

    def status(self, user: RegisteredUser, chat_id: int) -> CoffeeStatusReport:
        invitations_enabled = self._preferences.for_user(user.id).coffee_enabled
        session = self._sessions.get_open_for_chat(chat_id)
        if session is None:
            return CoffeeStatusReport(invitations_enabled, None, ())
        participants = self._sessions.list_participants(session.id)
        return CoffeeStatusReport(
            invitations_enabled,
            session.scheduled_at,
            tuple(participant.display_name for participant in participants),
        )

    async def create_or_reschedule(
        self,
        bot: Bot,
        chat_id: int,
        user: RegisteredUser,
        scheduled_at: datetime,
    ) -> None:
        async with self._locks.for_chat(chat_id):
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
                if is_new:
                    participants = self._sessions.list_participants(session.id)
                    await self._publisher.send_shout(bot, session, participants)
                session = await self._publish_card(bot, session)
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
                    raise RuntimeError("Created coffee card has no message id")
                session = self._sessions.activate(session.id, session.message_id)
            self._jobs.schedule_session(bot, session)
            await self._publisher.replace_pin(bot, previous_session, session)
            if not is_new and (
                previous_session is not None
                and previous_session.scheduled_at != session.scheduled_at
            ):
                await self._publisher.send_reschedule_notification(bot, user, session)

    async def update_participation(
        self,
        bot: Bot,
        user: RegisteredUser,
        callback: CoffeeCallbackData,
    ) -> Result[CoffeeParticipationReport, CoffeeErrorCode]:
        session = self._sessions.get(callback.session_id)
        if session is None or session.status != CoffeeSessionStatus.ACTIVE:
            return failure(CoffeeErrorCode.SESSION_ENDED)
        async with self._locks.for_chat(session.chat_id):
            current = self._sessions.get(callback.session_id)
            if current is None or current.status != CoffeeSessionStatus.ACTIVE:
                return failure(CoffeeErrorCode.SESSION_ENDED)
            participant_ids = {
                participant.id
                for participant in self._sessions.list_participants(current.id)
            }
            was_participant = user.id in participant_ids
            match callback.action:
                case CoffeeParticipantAction.JOIN:
                    if was_participant:
                        return success(
                            CoffeeParticipationReport(
                                CoffeeParticipationKind.UNCHANGED
                            )
                        )
                    self._sessions.join(current.id, user.id)
                    result_kind = CoffeeParticipationKind.JOINED
                case CoffeeParticipantAction.LEAVE:
                    if not was_participant:
                        return success(
                            CoffeeParticipationReport(
                                CoffeeParticipationKind.UNCHANGED
                            )
                        )
                    self._sessions.leave(current.id, user.id)
                    result_kind = CoffeeParticipationKind.LEFT
                case _:
                    assert_never(callback.action)
            try:
                updated = await self._publish_card(bot, current)
                await self._publisher.replace_pin(bot, current, updated)
            except Exception:
                if was_participant:
                    self._sessions.join(current.id, user.id)
                else:
                    self._sessions.leave(current.id, user.id)
                raise
            return success(CoffeeParticipationReport(result_kind))

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
