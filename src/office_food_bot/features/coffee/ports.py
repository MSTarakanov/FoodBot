from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date, datetime
from typing import Protocol

from office_food_bot.application.users.models import RegisteredUser
from office_food_bot.features.coffee.models import CoffeeSession, CoffeeSessionStatus
from office_food_bot.features.invitations.models import InvitationPreferences

AsyncJob = Callable[[], Awaitable[None]]


class CoffeeSessionStore(Protocol):
    def create(
        self,
        chat_id: int,
        initiator_user_id: int,
        scheduled_at: datetime,
    ) -> CoffeeSession: ...

    def activate(self, session_id: int, message_id: int) -> CoffeeSession: ...

    def update_message(self, session_id: int, message_id: int) -> CoffeeSession: ...

    def reschedule(
        self,
        session_id: int,
        proposer_user_id: int,
        scheduled_at: datetime,
    ) -> CoffeeSession: ...

    def get(self, session_id: int) -> CoffeeSession | None: ...

    def get_open_for_chat(self, chat_id: int) -> CoffeeSession | None: ...

    def list_recoverable(self) -> tuple[CoffeeSession, ...]: ...

    def join(self, session_id: int, user_id: int) -> None: ...

    def leave(self, session_id: int, user_id: int) -> None: ...

    def list_participants(self, session_id: int) -> tuple[RegisteredUser, ...]: ...

    def mark_completing(
        self,
        session_id: int,
        retry_until: datetime,
    ) -> CoffeeSession: ...

    def mark_retry(
        self,
        session_id: int,
        attempts: int,
        next_attempt_at: datetime,
    ) -> CoffeeSession: ...

    def mark_terminal(
        self,
        session_id: int,
        status: CoffeeSessionStatus,
        completed_at: datetime,
    ) -> CoffeeSession: ...


class CoffeeUserReader(Protocol):
    def get_by_id(self, user_id: int) -> RegisteredUser | None: ...


class CoffeeAttendance(Protocol):
    def list_office_users(
        self,
        chat_id: int,
        context_date: date,
    ) -> tuple[RegisteredUser, ...]: ...


class CoffeeInvitationPreferences(Protocol):
    def for_user(self, user_id: int) -> InvitationPreferences: ...


class CoffeeScheduler(Protocol):
    def add_date(self, job_id: str, callback: AsyncJob, run_at: datetime) -> None: ...

    def remove(self, job_id: str) -> None: ...
