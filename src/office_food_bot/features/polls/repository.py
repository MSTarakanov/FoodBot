from __future__ import annotations

import sqlite3
from collections.abc import Collection
from datetime import UTC, date, datetime

from office_food_bot.application.users.models import RegisteredUser, UserRole, UserStatus
from office_food_bot.database import Database
from office_food_bot.features.polls.models import PollKind, StoredPoll
from office_food_bot.features.polls.options import PollOption
from office_food_bot.features.polls.queries import (
    DELETE_SELECTED_POLL_OPTIONS_SQL,
    GET_LATEST_POLL_SQL,
    GET_POLL_SQL,
    INSERT_POLL_SQL,
    INSERT_SELECTED_POLL_OPTION_SQL,
    LIST_ACTIVE_USERS_WITH_SELECTED_OPTIONS_SQL,
    LIST_SELECTED_POLL_OPTIONS_SQL,
)


class PollRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, poll: StoredPoll) -> None:
        with self._database.connection:
            self._database.connection.execute(
                INSERT_POLL_SQL,
                (
                    poll.poll_id,
                    poll.chat_id,
                    poll.message_id,
                    poll.kind.value,
                    poll.context_date.isoformat(),
                    poll.published_at.isoformat(),
                ),
            )

    def get(self, poll_id: str) -> StoredPoll | None:
        row = self._database.connection.execute(GET_POLL_SQL, (poll_id,)).fetchone()
        if row is None:
            return None
        return _stored_poll_from_row(row)

    def latest_for_kinds(
        self,
        chat_id: int,
        context_date: date,
        kinds: Collection[PollKind],
    ) -> StoredPoll | None:
        requested_kinds = tuple(kinds)
        if not requested_kinds:
            return None
        placeholders = ", ".join("?" for _ in requested_kinds)
        row = self._database.connection.execute(
            GET_LATEST_POLL_SQL.format(kind_placeholders=placeholders),
            (
                chat_id,
                context_date.isoformat(),
                *(kind.value for kind in requested_kinds),
            ),
        ).fetchone()
        if row is None:
            return None
        return _stored_poll_from_row(row)

    def replace_selected_options(
        self,
        poll_id: str,
        telegram_user_id: int,
        options: Collection[PollOption],
        selected_at: datetime,
    ) -> frozenset[PollOption]:
        selected = frozenset(options)
        with self._database.connection:
            previous_rows = self._database.connection.execute(
                LIST_SELECTED_POLL_OPTIONS_SQL,
                (poll_id, telegram_user_id),
            ).fetchall()
            previous = frozenset(
                PollOption.from_value(str(row["option_key"]))
                for row in previous_rows
            )
            self._database.connection.execute(
                DELETE_SELECTED_POLL_OPTIONS_SQL,
                (poll_id, telegram_user_id),
            )
            self._database.connection.executemany(
                INSERT_SELECTED_POLL_OPTION_SQL,
                (
                    (poll_id, telegram_user_id, key.value, selected_at.isoformat())
                    for key in sorted(selected, key=lambda item: item.value)
                ),
            )
        return selected - previous

    def list_active_users_with_any_option(
        self,
        poll_id: str,
        options: Collection[PollOption],
    ) -> tuple[RegisteredUser, ...]:
        selected_options = tuple(options)
        if not selected_options:
            return ()
        placeholders = ", ".join("?" for _ in selected_options)
        query = LIST_ACTIVE_USERS_WITH_SELECTED_OPTIONS_SQL.format(
            option_placeholders=placeholders
        )
        rows = self._database.connection.execute(
            query,
            (
                poll_id,
                UserStatus.ACTIVE.value,
                *(option.value for option in selected_options),
            ),
        ).fetchall()
        return tuple(_registered_user_from_row(row) for row in rows)


def _stored_poll_from_row(row: sqlite3.Row) -> StoredPoll:
    published_at = datetime.fromisoformat(str(row["published_at"]))
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    return StoredPoll(
        poll_id=str(row["poll_id"]),
        chat_id=int(row["chat_id"]),
        message_id=int(row["message_id"]),
        kind=PollKind(str(row["kind"])),
        context_date=date.fromisoformat(str(row["context_date"])),
        published_at=published_at,
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


def _optional_str[Value](value: Value | None) -> str | None:
    if value is None:
        return None
    return str(value)
