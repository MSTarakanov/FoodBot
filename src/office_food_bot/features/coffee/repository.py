from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from office_food_bot.application.users.models import RegisteredUser, UserRole, UserStatus
from office_food_bot.database import Database
from office_food_bot.features.coffee.models import (
    CoffeeSession,
    CoffeeSessionStatus,
)
from office_food_bot.features.coffee.queries import (
    ACTIVATE_COFFEE_SESSION_SQL,
    CREATE_COFFEE_SESSION_SQL,
    DELETE_COFFEE_PARTICIPANT_SQL,
    GET_COFFEE_SESSION_SQL,
    GET_OPEN_COFFEE_SESSION_SQL,
    INSERT_COFFEE_PARTICIPANT_SQL,
    LIST_COFFEE_PARTICIPANTS_SQL,
    LIST_RECOVERABLE_COFFEE_SESSIONS_SQL,
    MARK_COFFEE_COMPLETING_SQL,
    MARK_COFFEE_RETRY_SQL,
    MARK_COFFEE_TERMINAL_SQL,
    RESCHEDULE_COFFEE_SESSION_SQL,
    UPDATE_COFFEE_MESSAGE_SQL,
)


class CoffeeSessionRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def create(
        self,
        chat_id: int,
        initiator_user_id: int,
        scheduled_at: datetime,
    ) -> CoffeeSession:
        with self._database.connection:
            cursor = self._database.connection.execute(
                CREATE_COFFEE_SESSION_SQL,
                (
                    chat_id,
                    initiator_user_id,
                    initiator_user_id,
                    scheduled_at.isoformat(),
                    CoffeeSessionStatus.CREATING.value,
                ),
            )
            session_id = cursor.lastrowid
            if session_id is None:
                msg = "Created coffee session id was not returned"
                raise RuntimeError(msg)
            self._database.connection.execute(
                INSERT_COFFEE_PARTICIPANT_SQL,
                (session_id, initiator_user_id),
            )
        return self.require(session_id)

    def activate(self, session_id: int, message_id: int) -> CoffeeSession:
        with self._database.connection:
            self._database.connection.execute(
                ACTIVATE_COFFEE_SESSION_SQL,
                (message_id, session_id),
            )
        return self.require(session_id)

    def update_message(self, session_id: int, message_id: int) -> CoffeeSession:
        with self._database.connection:
            self._database.connection.execute(
                UPDATE_COFFEE_MESSAGE_SQL,
                (message_id, session_id),
            )
        return self.require(session_id)

    def reschedule(
        self,
        session_id: int,
        proposer_user_id: int,
        scheduled_at: datetime,
    ) -> CoffeeSession:
        with self._database.connection:
            self._database.connection.execute(
                RESCHEDULE_COFFEE_SESSION_SQL,
                (proposer_user_id, scheduled_at.isoformat(), session_id),
            )
            self._database.connection.execute(
                INSERT_COFFEE_PARTICIPANT_SQL,
                (session_id, proposer_user_id),
            )
        return self.require(session_id)

    def get(self, session_id: int) -> CoffeeSession | None:
        row = self._database.connection.execute(
            GET_COFFEE_SESSION_SQL,
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return _coffee_session_from_row(row)

    def require(self, session_id: int) -> CoffeeSession:
        session = self.get(session_id)
        if session is None:
            msg = f"Coffee session {session_id} was not found"
            raise RuntimeError(msg)
        return session

    def get_open_for_chat(self, chat_id: int) -> CoffeeSession | None:
        row = self._database.connection.execute(
            GET_OPEN_COFFEE_SESSION_SQL,
            (chat_id,),
        ).fetchone()
        if row is None:
            return None
        return _coffee_session_from_row(row)

    def list_recoverable(self) -> tuple[CoffeeSession, ...]:
        rows = self._database.connection.execute(
            LIST_RECOVERABLE_COFFEE_SESSIONS_SQL
        ).fetchall()
        return tuple(_coffee_session_from_row(row) for row in rows)

    def join(self, session_id: int, user_id: int) -> None:
        with self._database.connection:
            self._database.connection.execute(
                INSERT_COFFEE_PARTICIPANT_SQL,
                (session_id, user_id),
            )

    def leave(self, session_id: int, user_id: int) -> None:
        with self._database.connection:
            self._database.connection.execute(
                DELETE_COFFEE_PARTICIPANT_SQL,
                (session_id, user_id),
            )

    def list_participants(self, session_id: int) -> tuple[RegisteredUser, ...]:
        rows = self._database.connection.execute(
            LIST_COFFEE_PARTICIPANTS_SQL,
            (session_id,),
        ).fetchall()
        return tuple(_registered_user_from_row(row) for row in rows)

    def mark_completing(
        self,
        session_id: int,
        retry_until: datetime,
    ) -> CoffeeSession:
        with self._database.connection:
            self._database.connection.execute(
                MARK_COFFEE_COMPLETING_SQL,
                (retry_until.isoformat(), session_id),
            )
        return self.require(session_id)

    def mark_retry(
        self,
        session_id: int,
        attempts: int,
        next_attempt_at: datetime,
    ) -> CoffeeSession:
        with self._database.connection:
            self._database.connection.execute(
                MARK_COFFEE_RETRY_SQL,
                (attempts, next_attempt_at.isoformat(), session_id),
            )
        return self.require(session_id)

    def mark_terminal(
        self,
        session_id: int,
        status: CoffeeSessionStatus,
        completed_at: datetime,
    ) -> CoffeeSession:
        with self._database.connection:
            self._database.connection.execute(
                MARK_COFFEE_TERMINAL_SQL,
                (status.value, completed_at.isoformat(), session_id),
            )
        return self.require(session_id)


def _coffee_session_from_row(row: sqlite3.Row) -> CoffeeSession:
    return CoffeeSession(
        id=int(row["id"]),
        chat_id=int(row["chat_id"]),
        message_id=_optional_int(row["message_id"]),
        initiator_user_id=int(row["initiator_user_id"]),
        last_proposer_user_id=int(row["last_proposer_user_id"]),
        scheduled_at=_datetime(str(row["scheduled_at"])),
        status=CoffeeSessionStatus(str(row["status"])),
        notification_attempts=int(row["notification_attempts"]),
        next_attempt_at=_optional_datetime(_optional_str(row["next_attempt_at"])),
        retry_until=_optional_datetime(_optional_str(row["retry_until"])),
    )


def _registered_user_from_row(row: sqlite3.Row) -> RegisteredUser:
    return RegisteredUser(
        id=int(row["id"]),
        telegram_user_id=int(row["telegram_user_id"]),
        display_name=str(row["display_name"]),
        status=UserStatus(str(row["status"])),
        role=UserRole(str(row["role"])),
        username=_optional_str(row["username"]),
        first_name=_optional_str(row["first_name"]),
        last_name=_optional_str(row["last_name"]),
    )


def _datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _optional_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return _datetime(value)


def _optional_int(value: int | None) -> int | None:
    return value


def _optional_str(value: str | None) -> str | None:
    return value
